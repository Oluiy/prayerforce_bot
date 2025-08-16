
from telegram.ext import *
from telegram import * 
from telegram.constants import ParseMode
from Prisma.prisma_connect import db
from services.Kora_service import KoraPayService


(EMAIL,) = range(1)

async def commands(app: Application):
    # Register commands in the bot's command menu
    commands_list = [
        BotCommand("start", "Get to know Tefillah"),
        BotCommand("announcement", "To get all necessary annoucement"),
        BotCommand("question", "Random questions from the database"),
        BotCommand("history", "Want to know the history of Prayer Force?🙂 you can 'use the command'"),
        BotCommand("Sunday_meetings", "Pre-service and Post-service"),
        BotCommand("Purchase_shirt", "Want to purchase shirt or Dd or both?"),
        BotCommand("donate", "Make a donation to Prayer Force"),
        BotCommand("donate_button", "Show donation button")
    ]

    await app.bot.set_my_comands(commands_list)


# Command handler functions for each command
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Prayer Force was founded in 2002 as a spiritual movement dedicated to prayer and intercession. "
        "Since then, we've grown into a community of believers committed to seeking God's presence through prayer."
    )

async def sunday_meetings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Our Sunday meetings schedule:\n\n"
        "Pre-service Prayer: 8:00 AM - 9:00 AM\n"
        "Main Service: 9:30 AM - 11:30 AM\n"
        "Post-service Prayer: 12:00 PM - 1:00 PM"
    )

async def purchase_shirt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display options for purchasing items."""
    keyboard = [
        [InlineKeyboardButton("FOOD + SHIRT", callback_data="add_to_cart:Food+Shirt:8500")],
        [InlineKeyboardButton("SHIRT", callback_data="add_to_cart:Shirt:6000")],
        [InlineKeyboardButton("FOOD", callback_data="add_to_cart:Food:2500")],
        [InlineKeyboardButton("View Cart", callback_data="view_cart")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = "🛍️ To purchase Prayer Force merch, click an item below to add it to your cart:"
    

    if update.callback_query:
        query = update.callback_query
        await query.answer() 
        await query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text=message_text,
            reply_markup=reply_markup
        )


async def handle_cart_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cart actions like adding items, adjusting quantities, and viewing the cart."""
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    action = data[0]
    user = update.effective_user

    # Get user from database
    db_user = await db.user.find_unique(where={"chatId": str(user.id)})
    if not db_user:
        await query.edit_message_text("Please start the bot first by sending /start")
        return

    if action == "add_to_cart" and len(data) >= 3:
        # When user selects an item, show quantity selection UI
        item_name = data[1]
        item_price = float(data[2])
        
        # Store item info in user_data for later use
        context.user_data['current_item'] = {
            'name': item_name,
            'base_price': item_price, 
            'price': item_price,      
            'quantity': 1              
        }
        
        
        await display_item_details(query, context)
        
    elif action == "quantity_+1":
        if 'current_item' in context.user_data:
            context.user_data['current_item']['quantity'] += 1
            base_price = context.user_data['current_item']['base_price']
            quantity = context.user_data['current_item']['quantity']
            context.user_data['current_item']['price'] = base_price * quantity
            await display_item_details(query, context)
            
    elif action == "quantity_-1":
        if 'current_item' in context.user_data and context.user_data['current_item']['quantity'] > 1:
            context.user_data['current_item']['quantity'] -= 1
            base_price = context.user_data['current_item']['base_price']
            quantity = context.user_data['current_item']['quantity']
            context.user_data['current_item']['price'] = base_price * quantity
            await display_item_details(query, context)
            
    elif action == "add_item_to_cart":
    # Actually add the item to cart with selected quantity
        if 'current_item' not in context.user_data:
            await query.edit_message_text("Error: No item selected.")
            return
            
        item = context.user_data['current_item']
        
        # Ensure the user has a cart
        cart = await db.cart.find_unique(where={"userId": db_user.id})
        if not cart:
            cart = await db.cart.create(data={"userId": db_user.id})
        
        # Check if item already exists in cart
        cart_item = await db.cartitem.find_first(
            where={"cartId": cart.id, "name": item['name']}
        )
        
        if cart_item:
            # Update quantity if item exists
            await db.cartitem.update(
                where={"id": cart_item.id},
                data={"quantity": cart_item.quantity + item['quantity']}
            )
        else:
            # Add new item - use base_price for the item price
            await db.cartitem.create(
                data={
                    "cartId": cart.id,
                    "name": item['name'],
                    "price": item['base_price'],  # Use base_price here
                    "quantity": item['quantity']
                }
            )
            
        await query.edit_message_text(
            f"✅ Added {item['quantity']} {item['name']} to your cart!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("View Cart", callback_data="view_cart")],
                [InlineKeyboardButton("Continue Shopping", callback_data="back_to_menu")]
            ])
        )
    elif action == "clear_cart":
        # Clear the cart and show confirmation
        await clear_cart(db_user.id)
        await query.edit_message_text(
            "🗑️ Your cart has been cleared.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")]
            ])
        )
            
    elif action == "view_cart":
        await display_cart(query, db_user.id)
        
    elif action == "back_to_menu":
        await purchase_shirt_command(update, context)
        
    elif action == "checkout":
        return await start_checkout(update, context)

async def display_item_details(query, context):
    """Display item details with quantity adjustment UI"""
    item = context.user_data['current_item']

    base_price = item['base_price']
    quantity = item['quantity']
    total_price = base_price * quantity

    message_text = (
        f"🌟 {item['name']} 🌟\n\n"
        f"Black shirt.\n\n"
        f"💰 Price: ₦ {total_price}\n"
        f"🔢 Quantity: {item['quantity']}\n"
        f"📍 Stall: Prayer Force\n\n"
        f"Use the buttons below to adjust quantity or add to cart."
    )

    keyboard = [
        [
            InlineKeyboardButton("Quantity -1", callback_data="quantity_-1"),
            InlineKeyboardButton("Quantity +1", callback_data="quantity_+1")
        ],
        [InlineKeyboardButton("Add to Cart", callback_data="add_item_to_cart")],
        [InlineKeyboardButton("View Cart", callback_data="view_cart")],
        [InlineKeyboardButton("Back", callback_data="back_to_menu")],
    ]
    
    await query.edit_message_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def display_cart(query, user_id):
    """Display the contents of the user's cart"""
    # Get the user's cart with items
    cart = await db.cart.find_unique(
        where={"userId": user_id},
        include={"items": True}
    )
    
    if not cart or not cart.items:
        await query.edit_message_text(
            "🛒 Your cart is empty.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")]
            ])
        )
        return
        
    # Generate cart summary
    message = "🛒 **Your Cart:**\n\n"
    total = 0
    
    for item in cart.items:
        subtotal = item.price * item.quantity
        message += f"• {item.name}: ₦{item.price} × {item.quantity} = ₦{subtotal}\n"
        total += subtotal
        
    message += f"\n**Total: ₦{total}**"
    
    # Create buttons for cart actions
    keyboard = [
        [InlineKeyboardButton("Checkout", callback_data="checkout")],
        [InlineKeyboardButton("Clear Cart", callback_data="clear_cart")],  # Added Clear Cart button
        [InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the checkout process"""
    query = update.callback_query
    await query.answer()

    # Retrieve the user ID from the database using the chat ID
    user = update.effective_user
    db_user = await db.user.find_unique(where={"chatId": str(user.id)})
    if not db_user:
        await query.edit_message_text("Please start the bot first by sending /start")
        return ConversationHandler.END

    # Store user ID in context for the payment handler
    context.user_data['checkout_user_id'] = db_user.id

    await query.edit_message_text(
        "Please enter your email address to proceed with checkout:"
    )

    # Set conversation state
    return EMAIL

async def process_checkout_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email submission for checkout process"""
    email = update.message.text.strip()
    
    # Basic email validation
    if '@' not in email or '.' not in email:
        await update.message.reply_text(
            "Please provide a valid email address."
        )
        return EMAIL  # Stay in EMAIL state to try again
    
    user_id = context.user_data.get('checkout_user_id')
    if not user_id:
        await update.message.reply_text(
            "Session expired. Please start the checkout process again."
        )
        return ConversationHandler.END
    
    # Get the user's cart
    cart = await db.cart.find_unique(
        where={"userId": user_id},
        include={"items": True}
    )
    
    if not cart or not cart.items:
        await update.message.reply_text("Your cart is empty.")
        return ConversationHandler.END
    
    # Calculate total price
    total_price = sum(item.price * item.quantity for item in cart.items)
    
    # Get user info
    db_user = await db.user.find_unique(where={"id": user_id})
    name = db_user.firstName or "Customer"
    
    item_names = [f"{item.quantity} {item.name}" for item in cart.items]
    
    kora_service = KoraPayService()
    payment_link_result = kora_service.generate_payment_link(
        amount=total_price, 
        name=name, 
        email=email
    )

    if not payment_link_result or payment_link_result[0] is None:
        await update.message.reply_text(
            "Sorry, we couldn't generate a payment link at this time. Please try again later."
        )
        return ConversationHandler.END
        
    payment_link, reference = payment_link_result
    
    await db.payment.create(
        data={
            "userId": user_id,
            "reference": reference,
            "amount": total_price,
            "email": email,
            "status": "pending"
        }
    )

    keyboard = [
        [InlineKeyboardButton("Pay Now", url=payment_link)],
        [InlineKeyboardButton("Verify Payment", callback_data=f"verify_payment:{reference}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📋 *Order Summary*\n\n"
        f"Items: {', '.join(item_names)}\n"
        f"Total: ₦{total_price}\n\n"
        f"Click the button below to complete your payment:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

async def clear_cart(user_id):
    """Clear all items in the user's cart."""
    cart = await db.cart.find_unique(where={"userId": user_id})
    if cart:
        # Delete all items in the cart
        await db.cartitem.delete_many(where={"cartId": cart.id})
        print(f"Cart cleared for user ID: {user_id}")
        return True
    return False

async def handle_payment_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify payment and clear the cart if successful."""
    query = update.callback_query
    await query.answer()
    
    # Extract payment reference from callback data
    reference = query.data.split(":")[1]
    user = update.effective_user
    
    # Find user in database
    db_user = await db.user.find_unique(where={"chatId": str(user.id)})
    if not db_user:
        await query.edit_message_text("User not found. Please start the bot with /start")
        return
    
    # Verify payment
    kora_service = KoraPayService()
    payment_successful = kora_service.verify_payment(reference)
    
    if payment_successful:
        # Update payment status in database
        await db.payment.update_many(
            where={"reference": reference},
            data={"status": "completed"}
        )
        
        # Clear the user's cart
        await clear_cart(db_user.id)
        
        # Show success message with order summary
        await query.edit_message_text(
            "✅ Payment successful! Your order has been confirmed.\n\n"
            "Thank you for your purchase! Your items will be ready for pickup.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")]
            ])
        )
    else:
        # Payment verification failed
        await query.edit_message_text(
            "❌ Payment verification failed or is still pending.\n\n"
            "Please try again in a few moments or contact us if you need assistance.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Try Again", callback_data=f"verify_payment:{reference}")],
                [InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")]
            ])
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Operation cancelled."
    )
    return ConversationHandler.END


# # Create command handlers
command_handler = CommandHandler("commands", commands)
history_handler = CommandHandler("history", history_command)
sunday_meetings_handler = CommandHandler("meetings", sunday_meetings_command)
purchase_shirt_handler = CommandHandler("merch", purchase_shirt_command)

# # Update the checkout conversation handler
checkout_conv_handler = ConversationHandler(
    entry_points=[
        # The pattern matches the checkout callback data
        CallbackQueryHandler(
            lambda u, c: start_checkout(u, c),
            pattern="^checkout$"
        )
    ],
    states={
        EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_checkout_email)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="checkout_conversation",
)