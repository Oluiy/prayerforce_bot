async def send_birthday_message(user, mates):
    msg = f"🎉 Happy Birthday, {user.firstName}!"

    if mates:
        mate_names = ", ".join([mate.firstName for mate in mates])
        msg += f"\nYou share your birthday with: {mate_names}!"

    # Replace this with actual Telegram bot sending or any messaging API
    print(f"To: {user.chatId} — {msg}")
