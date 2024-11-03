import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# 初始化机器人
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = '@naclyunpan'  # 替换为你的频道 Chat ID

# 临时存储用户投稿内容
user_posts = {}


# 启动命令，提供投稿模板
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    template_message = (
        "请按照以下格式投稿：\n\n"
        "图片\n\n"
        "名称：\n\n描述：\n\n链接：（夸克网盘）\n\n"
        "📁 大小：\n🏷 标签："
    )
    await update.message.reply_text(template_message)


# 处理用户的投稿消息
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 检查消息和聊天对象是否存在
    if update.message is None or update.message.chat is None:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="切勿在原文案上编辑，请重新发布。")
        return  # 确保消息存在且有效

    user_id = update.message.from_user.id

    # 检查投稿内容是否包含图片和文字
    if not update.message.photo or not update.message.caption:
        await update.message.reply_text("投稿格式不正确，请按照模板重新投稿。\n\n"
                                        "请按照以下格式投稿：\n\n"
                                        "图片\n\n"
                                        "名称：\n\n描述：\n\n链接：（夸克网盘）\n\n"
                                        "📁 大小：\n🏷 标签：")
        return

    # 获取图片和文字内容
    image = update.message.photo[-1].file_id
    caption = update.message.caption

    # 定义格式正则表达式
    pattern = (
        r"名称：\s*.*\n\n"
        r"描述：\s*.*\n\n"
        r"链接：\s*https:\/\/pan\.quark\.cn\/s\/[^\/]+\n\n"
        r"📁 大小：\s*.*\n"
        r"🏷 标签：\s*.*"
    )

    # 验证格式
    if not re.fullmatch(pattern, caption):
        await update.message.reply_text("投稿格式不正确，请按照模板重新投稿。\n\n"
                                        "请按照以下格式投稿：\n\n"
                                        "图片\n\n"
                                        "名称：\n\n描述：\n\n链接：（夸克网盘）\n\n"
                                        "📁 大小：\n🏷 标签：")
        return

    # 检查链接是否为夸克网盘链接
    quark_link_pattern = r"https:\/\/pan\.quark\.cn\/s\/[^\/]+"
    if not re.search(quark_link_pattern, caption):
        await update.message.reply_text("链接必须是夸克网盘的链接，请重新投稿。")
        return

    # 存储用户投稿内容以便之后编辑
    user_posts[user_id] = {'image': image, 'caption': caption}

    # 提供确认和编辑按钮
    keyboard = [
        [InlineKeyboardButton("编辑", callback_data="edit_post")],
        [InlineKeyboardButton("确认发布", callback_data="confirm_post")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 确认并提示用户可以编辑
    await update.message.reply_text("感谢您的投稿！您可以选择编辑或确认发布到频道：", reply_markup=reply_markup)


# 处理编辑按钮的回调
async def handle_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    # 确保回应按钮点击事件
    await query.answer()

    # 检查当前消息内容
    current_text = query.message.text
    new_text = "请发送新的投稿内容，格式与之前相同。"

    # 只有在新内容不同的情况下，才进行编辑
    if current_text != new_text:
        await query.edit_message_text(new_text)
    else:
        await query.answer("消息内容未改变。", show_alert=True)


# 更新投稿内容
async def update_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # 检查用户是否处于编辑状态
    if context.user_data.get('editing'):
        new_text = update.message.text

        # 更新投稿内容
        if user_id in user_posts:
            user_posts[user_id]['caption'] = new_text
            await update.message.reply_text("您的投稿内容已更新！")
            # 清除编辑状态
            context.user_data['editing'] = False
        else:
            await update.message.reply_text("没有找到可编辑的投稿内容。")
    else:
        await update.message.reply_text("请先使用编辑按钮来编辑您的投稿内容。")


# 确认发布到频道的回调
async def handle_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    # 检查用户是否有投稿内容
    if user_id in user_posts:
        post_data = user_posts[user_id]
        image = post_data['image']
        caption = post_data['caption']

        # 构建频道消息内容
        channel_message = (
            f"{caption}\n\n"
            f"📢 频道：@naclyunpan"
        )

        # 发送图片和文字到频道
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=image, caption=channel_message)

        # 回复用户投稿成功，并从临时存储中删除内容
        await query.answer("内容已成功发布到频道！")
        await query.edit_message_text("您的投稿已成功发布到频道。感谢您的支持！")
        del user_posts[user_id]
    else:
        await query.answer("找不到您的投稿内容，无法发送到频道。")


def main():
    # 创建应用程序实例
    application = Application.builder().token(TOKEN).build()

    # 添加命令处理器
    application.add_handler(CommandHandler("start", start))

    # 添加消息处理器，处理首次投稿和更新内容
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    # 添加编辑和确认回调处理器
    application.add_handler(CallbackQueryHandler(handle_edit_callback, pattern="edit_post"))
    application.add_handler(CallbackQueryHandler(handle_confirm_callback, pattern="confirm_post"))

    # 添加更新消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, update_post))

    # 开始轮询更新
    application.run_polling()


if __name__ == '__main__':
    main()
