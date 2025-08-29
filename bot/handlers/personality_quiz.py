from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode
import time
from datetime import datetime
from Prisma.prisma_connect import db

# Conversation states
QUIZ_ACTIVE = 1

# Define personality quiz questions
personality_questions = [
    {
        "text": "When facing a difficult situation, what do you usually do first?",
        "options": [
            {"text": "Pray immediately", "category": "Spiritual"},
            {"text": "Analyze the problem", "category": "Analytical"},
            {"text": "Seek advice from others", "category": "Social"},
            {"text": "Take time to reflect", "category": "Reflective"}
        ]
    },
    {
        "text": "How do you prefer to serve in ministry?",
        "options": [
            {"text": "Leading worship", "category": "Leadership"},
            {"text": "Teaching/Preaching", "category": "Teaching"},
            {"text": "Helping behind the scenes", "category": "Service"},
            {"text": "Counseling others", "category": "Pastoral"}
        ]
    },
    {
        "text": "What motivates you most in your spiritual journey?",
        "options": [
            {"text": "Growing closer to God", "category": "Spiritual"},
            {"text": "Understanding scripture better", "category": "Teaching"},
            {"text": "Helping others grow", "category": "Pastoral"},
            {"text": "Making a difference", "category": "Service"}
        ]
    },
    {
        "text": "In a group prayer session, you are most likely to:",
        "options": [
            {"text": "Lead the prayer", "category": "Leadership"},
            {"text": "Pray silently", "category": "Reflective"},
            {"text": "Share prayer requests", "category": "Social"},
            {"text": "Support others in prayer", "category": "Service"}
        ]
    },
    {
        "text": "When studying the Bible, you prefer to:",
        "options": [
            {"text": "Study alone with God", "category": "Spiritual"},
            {"text": "Research historical context", "category": "Analytical"},
            {"text": "Discuss with others", "category": "Social"},
            {"text": "Apply it practically", "category": "Service"}
        ]
    },
    {
        "text": "How do you handle spiritual challenges?",
        "options": [
            {"text": "Fast and pray", "category": "Spiritual"},
            {"text": "Study relevant scriptures", "category": "Teaching"},
            {"text": "Seek pastoral guidance", "category": "Pastoral"},
            {"text": "Trust God and wait", "category": "Reflective"}
        ]
    },
    {
        "text": "What type of ministry excites you most?",
        "options": [
            {"text": "Evangelism", "category": "Leadership"},
            {"text": "Youth ministry", "category": "Teaching"},
            {"text": "Community service", "category": "Service"},
            {"text": "Intercession ministry", "category": "Spiritual"}
        ]
    }
]

async def start_personality_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the personality quiz"""
    # Initialize quiz data
    context.user_data['quiz_started'] = True
    context.user_data['current_question'] = 0
    context.user_data['quiz_answers'] = []
    context.user_data['category_scores'] = {
        'Spiritual': 0,
        'Leadership': 0,
        'Teaching': 0,
        'Service': 0,
        'Pastoral': 0,
        'Analytical': 0,
        'Social': 0,
        'Reflective': 0
    }
    context.user_data['quiz_start_time'] = time.time()
    
    await update.message.reply_text(
        "🌟 *Prayer Force Spiritual Gifts Assessment*\n\n"
        "This quiz will help you discover your spiritual gifts and ministry calling. "
        "Answer honestly based on your natural tendencies.\n\n"
        "Ready to begin?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Start Quiz ✨", callback_data="start_quiz")]
        ])
    )
    return QUIZ_ACTIVE

async def show_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display current quiz question with progress"""
    query = update.callback_query
    await query.answer()
    
    current_q = context.user_data.get('current_question', 0)
    total_questions = len(personality_questions)
    
    if current_q >= total_questions:
        return await show_quiz_results(update, context)
    
    question = personality_questions[current_q]
    
    # Create progress indicator
    progress = f"[{current_q + 1}/{total_questions}]"
    
    # Create options as inline keyboard
    keyboard = []
    for i, option in enumerate(question['options']):
        keyboard.append([
            InlineKeyboardButton(
                f"○ {option['text']}", 
                callback_data=f"answer_{i}"
            )
        ])
    
    # Add timer display (you can implement actual countdown if needed)
    elapsed_time = int(time.time() - context.user_data.get('quiz_start_time', time.time()))
    timer_display = f"⏱️ {elapsed_time//60}:{elapsed_time%60:02d}"
    
    message_text = (
        f"{progress} {question['text']}\n\n"
        f"Choose your answer:\n\n"
        f"{timer_display}"
    )
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return QUIZ_ACTIVE

async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz answer selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_quiz":
        return await show_quiz_question(update, context)
    
    if query.data.startswith("answer_"):
        answer_index = int(query.data.split("_")[1])
        current_q = context.user_data.get('current_question', 0)
        
        # Record the answer
        question = personality_questions[current_q]
        selected_option = question['options'][answer_index]
        
        context.user_data['quiz_answers'].append({
            'question': current_q,
            'answer': answer_index,
            'category': selected_option['category']
        })
        
        # Update category scores
        category = selected_option['category']
        context.user_data['category_scores'][category] += 1
        
        # Move to next question
        context.user_data['current_question'] = current_q + 1
        
        return await show_quiz_question(update, context)
    
    return QUIZ_ACTIVE

async def show_quiz_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display quiz results with percentages"""
    query = update.callback_query
    
    total_questions = len(personality_questions)
    category_scores = context.user_data.get('category_scores', {})
    
    # Calculate percentages
    results_text = "🎉 *Spiritual Gifts Assessment Results*\n\n"
    results_text += "*Your Ministry Profile:*\n\n"
    
    # Sort categories by score (highest first)
    sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
    
    for category, score in sorted_categories:
        percentage = int((score / total_questions) * 100) if total_questions > 0 else 0
        
        # Create visual bar
        filled_bars = percentage // 10
        bar = "█" * filled_bars + "░" * (10 - filled_bars)
        
        results_text += f"{percentage}% {category}\n{bar}\n\n"
    
    # Add interpretation
    top_category = sorted_categories[0][0] if sorted_categories else "Balanced"
    interpretations = {
        'Spiritual': 'You have a strong calling for intercession and spiritual warfare. Consider joining the prayer team or intercession ministry.',
        'Leadership': 'You have natural leadership gifts. Consider roles in ministry leadership or starting new initiatives.',
        'Teaching': 'You have a gift for explaining and teaching. Consider joining the teaching ministry or small group leadership.',
        'Service': 'You have a heart for practical service. Consider joining the hospitality or community service teams.',
        'Pastoral': 'You have a gift for caring and counseling. Consider joining the pastoral care or counseling ministry.',
        'Analytical': 'You have a gift for research and deep study. Consider joining the study groups or curriculum development.',
        'Social': 'You connect well with others. Consider evangelism or community outreach ministries.',
        'Reflective': 'You have a contemplative nature. Consider joining contemplative prayer or meditation ministries.'
    }
    
    results_text += f"*Primary Gift: {top_category}*\n\n"
    results_text += f"💡 *Recommendation:*\n{interpretations.get(top_category, 'You have a balanced spiritual profile!')}\n\n"
    
    # Add final encouragement
    results_text += "Remember: These are gifts, not limitations. God can use you in many ways! 🙏"
    
    # Clear quiz data
    context.user_data.pop('quiz_started', None)
    context.user_data.pop('current_question', None)
    context.user_data.pop('quiz_answers', None)
    context.user_data.pop('category_scores', None)
    context.user_data.pop('quiz_start_time', None)
    
    keyboard = [
        [InlineKeyboardButton("Take Quiz Again 🔄", callback_data="retake_quiz")],
        [InlineKeyboardButton("Share Results 📤", callback_data="share_results")]
    ]
    
    await query.edit_message_text(
        text=results_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

async def handle_retake_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle retaking the quiz"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "retake_quiz":
        return await start_personality_quiz(update, context)
    elif query.data == "share_results":
        await query.edit_message_text("Feature coming soon! 📤")
        return ConversationHandler.END
    
    return ConversationHandler.END

async def cancel_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the quiz"""
    await update.message.reply_text("Quiz cancelled. You can start again anytime with /personality")
    return ConversationHandler.END

# Create the conversation handler
personality_quiz_handler = ConversationHandler(
    entry_points=[CommandHandler("personality", start_personality_quiz)],
    states={
        QUIZ_ACTIVE: [CallbackQueryHandler(handle_quiz_answer)],
    },
    fallbacks=[CommandHandler("cancel", cancel_quiz)],
    allow_reentry=True,
)
