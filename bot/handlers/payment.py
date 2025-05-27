from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode
from services.Kora_service import KoraPayService
from Prisma.prisma_connect import db

# Conversation states
EMAIL, AMOUNT, CONFIRM = range(3)

kora_service = KoraPayService()

async def payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the payment process when the user enters the /donate command"""
    user = update.effective_user
    
    await update.message.reply_text(
        f"Hello {user.first_name}! Thank you for your willingness to contribute.\n\n"
        "Please enter your email address for payment confirmation:"
    )
    
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the email and ask for the amount"""
    email = update.message.text
    
    # Basic email validation
    if "@" not in email or "." not in email:
        await update.message.reply_text(
            "Please enter a valid email address."
        )
        return EMAIL
        
    context.user_data['email'] = email
    
    await update.message.reply_text(
        "Thank you! Now, please enter the amount you'd like to contribute (in Naira):"
    )
    
    return AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the amount and ask for confirmation"""
    try:
        amount = float(update.message.text)
        if amount <= 0:
            raise ValueError("Amount must be positive")
            
        context.user_data['amount'] = amount
        
        keyboard = [
            [
                InlineKeyboardButton("Confirm", callback_data="payment_confirm"),
                InlineKeyboardButton("Cancel", callback_data="payment_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"You're about to donate ₦{amount:.2f} to Prayer Force.\n\n"
            f"Email: {context.user_data['email']}\n"
            "Is this correct?",
            reply_markup=reply_markup
        )
        
        return CONFIRM
        
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid amount (numbers only)."
        )
        return AMOUNT

async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the confirmation callback"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "payment_cancel":
        await query.edit_message_text("Payment cancelled. Thank you for considering!")
        return ConversationHandler.END
        
    if query.data == "payment_confirm":
        user = update.effective_user
        
        # Generate payment link
        try:
            checkout_url, reference = kora_service.generate_payment_link(
                amount=context.user_data['amount'],
                name=user.full_name or f"{user.first_name} {user.last_name or ''}".strip(),
                email=context.user_data['email'],
                description="Prayer Force Donation"
            )
        except Exception as e:
            print(f"Error in payment process: {str(e)}")
            await query.edit_message_text(
                "Sorry, there was an issue with the payment system. Please try again later."
            )
            return ConversationHandler.END
        
        
        if checkout_url:

            db_user = await db.user.find_unique(
                where={"chatId": str(user.id)}
            )

            await db.payment.create(
                data={
                    "userId": db_user.id,
                    "amount": context.user_data['amount'],
                    "reference": reference,
                    "status": "pending",
                    "email": context.user_data['email']
                }
            )
            
            keyboard = [[InlineKeyboardButton("Make Payment", url=checkout_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Thank you for your contribution! Click the button below to complete your payment.",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                "Sorry, there was an issue generating your payment link. Please try again later."
            )
            
        return ConversationHandler.END

async def payment_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback function for the conversation handler"""
    await update.message.reply_text(
        "Payment process cancelled. You can start again with /donate command."
    )
    return ConversationHandler.END

# Create the conversation handler for the payment flow
payment_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("donate", payment_start)],
    states={
        EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
        CONFIRM: [CallbackQueryHandler(handle_payment_callback, pattern=r"^payment_")]
    },
    fallbacks=[CommandHandler("cancel", payment_fallback)]
)

# Direct payment button handler
async def send_payment_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a payment button directly"""
    keyboard = [
        [InlineKeyboardButton("Make a Donation", callback_data="start_donation")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Support Prayer Force Ministry with your contribution:",
        reply_markup=reply_markup
    )

async def payment_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the payment button callback"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_donation":
        await query.edit_message_text("Let's start the donation process!")
        return await payment_start(update, context)
    
    return None

# Create a payment button handler
payment_button_handler = CallbackQueryHandler(
    payment_button_callback, 
    pattern=r"^start_donation$"
)

payment_callback_handler = CallbackQueryHandler(
    handle_payment_callback, 
    pattern=r"^payment_"
)