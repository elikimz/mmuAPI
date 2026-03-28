from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime, time, timedelta, timezone
import io
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from passlib.context import CryptContext

from app.models.models import User, Withdrawal, Wallet, Transaction
from app.database.database import get_async_db
from app.routers.auth import get_current_user, get_current_admin
from app.schema.schema import (
    WithdrawalCreate,
    WithdrawalResponse,
    WithdrawalUpdateStatus,
)

class WithdrawalReceipt(FPDF):
    def __init__(self, serial_number=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_number = serial_number

    def header(self):
        # UKB Logo
        logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "ukb_logo.png")
        if os.path.exists(logo_path):
            self.image(logo_path, x=10, y=8, w=30)
        
        # Company Name
        self.set_font('helvetica', 'B', 20)
        self.set_text_color(79, 70, 229) # Indigo color
        self.set_xy(45, 10)
        self.cell(0, 10, 'UKB PLATFORM', 0, 1, 'L')
        
        # Receipt Title
        self.set_font('helvetica', '', 10)
        self.set_text_color(100, 116, 139)
        self.set_xy(45, 18)
        self.cell(0, 10, 'Official Withdrawal Receipt', 0, 1, 'L')

        # Unique Serial Number at the edge
        if self.serial_number:
            self.set_font('helvetica', 'B', 7)
            self.set_text_color(148, 163, 184)
            # Position at top right edge
            self.set_xy(155, 8)
            # Draw dotted box for serial number
            self.dashed_line(155, 8, 205, 8, 0.5, 0.5)
            self.dashed_line(155, 15, 205, 15, 0.5, 0.5)
            self.dashed_line(155, 8, 155, 15, 0.5, 0.5)
            self.dashed_line(205, 8, 205, 15, 0.5, 0.5)
            self.cell(50, 7, f'SERIAL: {self.serial_number}', 0, 0, 'C')
            
        self.ln(15)

    def footer(self):
        self.set_y(-25)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(148, 163, 184)
        self.dashed_line(10, self.get_y(), 200, self.get_y(), 1, 1)
        self.ln(5)
        self.cell(0, 5, 'This is a computer-generated receipt and does not require a signature.', 0, 1, 'C')
        self.cell(0, 5, 'Thank you for using UKB Platform!', 0, 1, 'C')
        self.cell(0, 5, f'Page {self.page_no()}', 0, 0, 'C')

router = APIRouter(prefix="/withdrawals", tags=["Withdrawals"])

# -------------------------
# CONFIG
# -------------------------
TAX_RATE = 0.10  # 10%
pwd_context_pin = CryptContext(schemes=["argon2"], deprecated="auto")
ARGON2_MAX_LENGTH = 128
KENYA_TZ = timezone(timedelta(hours=3))  # UTC+3

# -------------------------
# UTILS
# -------------------------
def verify_pin(plain_pin, hashed_pin):
    return pwd_context_pin.verify(plain_pin, hashed_pin)

def get_hashed_pin(pin):
    return pwd_context_pin.hash(pin)

# -------------------------
# ROUTES
# -------------------------

@router.post("/", response_model=WithdrawalResponse)
async def create_withdrawal(
    withdrawal_data: WithdrawalCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Check if user has a withdrawal PIN set
    if not current_user.withdrawal_pin:
        raise HTTPException(status_code=400, detail="Please set a withdrawal PIN first")

    # 2. Verify PIN
    if not verify_pin(withdrawal_data.pin, current_user.withdrawal_pin):
        raise HTTPException(status_code=400, detail="Invalid withdrawal PIN")

    # 3. Check balance (Withdrawal from income only)
    result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalar_one_or_none()

    available_income = wallet.income if wallet else 0.0

    if not wallet or available_income < withdrawal_data.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient withdrawable income. Available: KES {available_income:,.2f}"
        )

    # 4. Create withdrawal record
    tax = withdrawal_data.amount * TAX_RATE
    net_amount = withdrawal_data.amount - tax

    new_withdrawal = Withdrawal(
        user_id=current_user.id,
        name=withdrawal_data.name,
        number=withdrawal_data.number,
        amount=withdrawal_data.amount,
        tax=tax,
        net_amount=net_amount,
        status="pending"
    )

    # 5. Deduct from wallet income
    wallet.income -= withdrawal_data.amount
    
    transaction = Transaction(
        user_id=current_user.id,
        amount=withdrawal_data.amount,
        type="withdrawal",
        description=f"Withdrawal request of KES {withdrawal_data.amount}",
        status="pending"
    )
    
    db.add(new_withdrawal)
    db.add(transaction)
    await db.commit()
    await db.refresh(new_withdrawal)
    
    return new_withdrawal

@router.get("/me", response_model=List[WithdrawalResponse])
async def get_my_withdrawals(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Withdrawal)
        .where(Withdrawal.user_id == current_user.id)
        .order_by(Withdrawal.created_at.desc())
    )
    return result.scalars().all()

@router.get("/", response_model=List[WithdrawalResponse])
async def get_all_withdrawals(
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Withdrawal).order_by(Withdrawal.created_at.desc())
    )
    return result.scalars().all()

@router.put("/{withdrawal_id}", response_model=WithdrawalResponse)
async def update_withdrawal_status(
    withdrawal_id: int,
    status_data: WithdrawalUpdateStatus,
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin)
):
    result = await db.execute(select(Withdrawal).where(Withdrawal.id == withdrawal_id))
    withdrawal = result.scalar_one_or_none()
    
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    if withdrawal.status != "pending":
        raise HTTPException(status_code=400, detail="Withdrawal already processed")
    
    withdrawal.status = status_data.status
    
    # Update associated transaction
    trans_result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == withdrawal.user_id)
        .where(Transaction.type == "withdrawal")
        .where(Transaction.amount == withdrawal.amount)
        .where(Transaction.status == "pending")
        .order_by(Transaction.created_at.desc())
    )
    transaction = trans_result.scalars().first()
    
    if transaction:
        transaction.status = status_data.status
        
    # If rejected, refund the wallet (return to income since that is the primary source)
    if status_data.status == "rejected":
        wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == withdrawal.user_id))
        wallet = wallet_result.scalar_one_or_none()
        if wallet:
            wallet.income += withdrawal.amount
            
    await db.commit()
    await db.refresh(withdrawal)
    return withdrawal

@router.post("/set-pin")
async def set_withdrawal_pin(
    pin_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    pin = pin_data.get("pin")
    if not pin or len(pin) < 4:
        raise HTTPException(status_code=400, detail="PIN must be at least 4 digits")
    
    current_user.withdrawal_pin = get_hashed_pin(pin)
    await db.commit()
    return {"message": "Withdrawal PIN set successfully"}

@router.get("/{withdrawal_id}/receipt")
async def download_receipt(
    withdrawal_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch withdrawal
    result = await db.execute(
        select(Withdrawal).where(Withdrawal.id == withdrawal_id)
    )
    withdrawal = result.scalar_one_or_none()

    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    # Security check: only owner or admin can download
    if withdrawal.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to access this receipt")
    
    if withdrawal.status != "approved":
        raise HTTPException(status_code=400, detail="Receipt only available for approved withdrawals")
    
    # Generate Unique Serial Number
    # Format: UKB-WDR-[ID]-[USER_ID]-[TIMESTAMP_SUFFIX]
    timestamp_suffix = int(withdrawal.created_at.timestamp()) % 10000
    serial_number = f"UKB-WDR-{withdrawal.id:04d}-{withdrawal.user_id:04d}-{timestamp_suffix:04d}"

    # Create PDF
    pdf = WithdrawalReceipt(serial_number=serial_number)
    pdf.add_page()
    
    # Receipt Details Box
    pdf.set_fill_color(248, 250, 252) # Light gray background
    pdf.rect(10, 35, 190, 30, 'F')
    pdf.set_draw_color(203, 213, 225) # Light blue-gray for borders
    pdf.dashed_line(10, 35, 200, 35, 1, 1)
    pdf.dashed_line(10, 65, 200, 65, 1, 1)
    
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(30, 41, 59) # Dark blue-gray text
    pdf.set_xy(15, 40)
    pdf.cell(90, 10, f'Receipt No: #WDR-{withdrawal.id:06d}')
    pdf.set_xy(110, 40)
    pdf.cell(90, 10, f'Date: {withdrawal.created_at.strftime("%Y-%m-%d %H:%M")}', 0, 0, 'R')
    
    pdf.set_font('helvetica', '', 10)
    pdf.set_xy(15, 50)
    pdf.cell(90, 10, f'Status: {withdrawal.status.upper()}')
    pdf.set_xy(110, 50)
    pdf.cell(90, 10, f'User ID: {withdrawal.user_id}', 0, 0, 'R')
    
    pdf.ln(25)
    
    # Transaction Details Table Header
    pdf.set_fill_color(79, 70, 229) # Indigo header background
    pdf.set_text_color(255, 255, 255) # White text
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(130, 10, ' Description', 1, 0, 'L', True)
    pdf.cell(60, 10, ' Amount (KES)', 1, 1, 'R', True)
    
    # Table Body
    pdf.set_text_color(30, 41, 59) # Dark blue-gray text
    pdf.set_font('helvetica', '', 10)
    
    # Row 1: Gross Amount
    pdf.set_fill_color(240, 244, 255) # Light indigo for alternating rows
    pdf.cell(130, 10, ' Withdrawal Amount (Gross)', 'LR', 0, 'L', True)
    pdf.cell(60, 10, f' {withdrawal.amount:,.2f}', 'R', 1, 'R', True)
    
    # Row 2: Tax
    pdf.set_fill_color(255, 255, 255) # White for alternating rows
    pdf.set_text_color(220, 38, 38) # Red for tax
    pdf.cell(130, 10, ' Processing Tax (10%)', 'LR', 0, 'L', True)
    pdf.cell(60, 10, f' -{withdrawal.tax:,.2f}', 'R', 1, 'R', True)
    
    # Row 3: Net Amount
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(16, 185, 129) # Green for net
    pdf.set_fill_color(240, 253, 244) # Light green for net amount row
    pdf.cell(130, 12, ' Net Amount Paid', 'LRB', 0, 'L', True)
    pdf.cell(60, 12, f' {withdrawal.net_amount:,.2f}', 'RB', 1, 'R', True)
    
    pdf.ln(10)
    
    # Recipient Details
    pdf.set_text_color(71, 85, 105) # Gray-blue text
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 10, 'Recipient Details:', 0, 1, 'L')
    pdf.set_font('helvetica', '', 10)
    pdf.cell(40, 8, 'Name:', 0, 0)
    pdf.cell(0, 8, withdrawal.name, 0, 1)
    pdf.cell(40, 8, 'M-Pesa Number:', 0, 0)
    pdf.cell(0, 8, withdrawal.number, 0, 1)
    
    pdf.ln(15)
    
    # Security Note
    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(0, 5, 'Note: This withdrawal has been processed and sent to the registered M-Pesa number. If you have any issues, please contact support with the Receipt Number above.', 0, 'L')

    # Output PDF to bytes
    try:
        # In fpdf2, output() returns bytes or bytearray
        pdf_output = pdf.output()
        
        # Ensure we have bytes for the Response
        if isinstance(pdf_output, (bytearray, memoryview)):
            pdf_output = bytes(pdf_output)
        elif isinstance(pdf_output, str):
            # Fallback for very old fpdf versions
            pdf_output = pdf_output.encode('latin-1')
            
        return Response(
            content=pdf_output,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=UKB_Receipt_WDR_{withdrawal.id}.pdf",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        import traceback
        from app.main import logger
        logger.error(f"PDF Generation Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
