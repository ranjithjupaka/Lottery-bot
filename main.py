import re
import time
from config import contract_addr, contract_abi, url,provider_url
from web3 import Web3, constants
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

w3 = Web3(Web3.HTTPProvider(provider_url))

contract = w3.eth.contract(address=contract_addr, abi=contract_abi)

TOKEN, VALUE, NUM, BET, RESULT, RETRY = range(6)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /start is issued."""
    await update.message.reply_html(
        "Hi I am your BetDapp bot\nEnter your Token to Authenticate your account and Play games",
        reply_markup=ReplyKeyboardRemove()
    )

    return TOKEN


async def authenticate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Authentication"""
    reply_keyboard = [["Place Your Bet"], ["Pool Balance", "Account Balance"], ["Share and Reward", "Instructions"]]

    user_msg = update.message.text
    print(user_msg)

    addr =  contract.functions.authCodes(user_msg).call()
    print(addr)
    if addr == constants.ADDRESS_ZERO:
        print("Invalid Authcode")
        context.user_data["attempts"] = 1

        await update.message.reply_text("Invalid token. Please try again:")
        return RETRY
    else:
        context.user_data["authenticated"] = True
        context.user_data["user_address"] = addr
        context.user_data["auth_tkn"] = user_msg
        await update.message.reply_text("You are Authenticated Successfully", reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Select a Option"
        ))

    return ConversationHandler.END


async def retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["Place Your Bet"], ["Pool Balance", "Account Balance"], ["Share and Reward", "Instructions"]]

    user_msg = update.message.text
    print(user_msg)

    addr =  contract.functions.authCodes(user_msg).call()
    print(addr == constants.ADDRESS_ZERO)

    if addr == constants.ADDRESS_ZERO:
        print("Invalid Authcode")
        context.user_data["attempts"] += 1

        if context.user_data["attempts"] >= 3:
            await update.message.reply_text("Too many invalid attempts. Please try again later.")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Invalid token. Please try again:")
            return RETRY
    else:
        context.user_data["authenticated"] = True
        context.user_data["user_address"] = addr
        context.user_data["auth_tkn"] = user_msg

        await update.message.reply_text("You are Authenticated Successfully", reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Select a Option"
        ))

    return ConversationHandler.END


async def get_user_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays Balance"""
    addr = context.user_data["user_address"]
    bal =  contract.functions.getUserBalance(addr).call()
    print(bal)
    usdt_value = bal / (10 ** 18)

    if usdt_value == 0:
        await update.message.reply_text(
            f"Your Balance is 0\n Go to website {url} and Deposit Crypto to Play games")
    else:
        await update.message.reply_text(
            f"Your Balance is {usdt_value}")


async def get_pool_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays Balance"""
    bal =  contract.functions.contractBalance().call()
    print(bal)
    usdt_value = bal / (10 ** 18)
    await update.message.reply_text(f"Pool Balance is {usdt_value}")


async def get_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays Balance"""
    inst = "Game rules:\n1. Select a number from 0 to 9.\n"
    inst += "2. Wager an amount (minimum 3, maximum 999).\n 3. The smart contract generates a random number within the 0 to 9 range.\n"
    inst += "4. If your chosen number matches the generated number, you win 10 times the wagered amount.\n\n"
    inst += " - The house retains a 3% deduction.\n"
    inst += " - If the numbers do not match, the wagered amount is added to the Jackpot.\n"
    inst += " - The house is responsible for covering losses up to the Jackpot's maximum value.\n"

    await update.message.reply_text(inst)


async def place_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Enter Bet Amount (3 to 999) in USDT")
    return BET


async def get_num(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text

    addr = context.user_data["user_address"]
    bal =  contract.functions.getUserBalance(addr).call()
    print(bal)
    usdt_value = bal / (10 ** 18)

    if float(user_input) > usdt_value:
        await update.message.reply_text(f"Your Balance is Insufficient\n Please Fund your account to Place the bet")
        return ConversationHandler.END
    else:
        context.user_data['bet'] = float(user_input)
        await update.message.reply_text("Choose and Enter a Number between 0 and 9")
        return NUM


async def get_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    input_num = update.message.text
    bet = context.user_data['bet']
    bet = bet*(10**18)
    authcode = context.user_data["auth_tkn"]
    result =  contract.functions.playGameTelegram(int(bet), int(input_num), authcode,{ gasLimit: 500000 }).call()
    print(result)
    rand_num =  contract.functions.randomNumber().call()
    rand_num = rand_num % 10

    if input_num == rand_num:
        await update.message.reply_text(f"Number Drawn by the smart contract is {rand_num}\n Hurray you won the bet")
    else:
        await update.message.reply_text(f"Number Drawn by the smart contract is {rand_num}\n Sorry you lost the bet")

    return ConversationHandler.END


async def share_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Share Refferal link"""
    addr = context.user_data["user_address"]
    ref_tkn =  contract.functions.getRefferalToken(addr).call()
    # refferals = contract.functions.refferals(addr).call()
    print(ref_tkn)
    await update.message.reply_text(
        f"Refer your Friends and Earn Rewards using the following link\n {url}?ref={ref_tkn}\n\n You'll receive the full amount of your friend's bet every time they win. For instance, if your friend bets 100 and wins, you'll receive 100.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""

    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    application = Application.builder().token("6433676050:AAHvEnne4tsgLcJL0urj_ujXiuYUPFNO9mU").build()

    auth_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TOKEN: [MessageHandler(filters.TEXT, authenticate)],
            RETRY: [MessageHandler(filters.TEXT, retry)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    bet_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("Place Your Bet"), place_bet)],
        states={
            BET: [MessageHandler(filters.TEXT, get_num)],
            NUM: [MessageHandler(filters.TEXT, get_results)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(auth_handler)
    application.add_handler(bet_handler)
    application.add_handler(MessageHandler(filters.Regex("Pool Balance"), get_pool_balance))
    application.add_handler(MessageHandler(filters.Regex("Account Balance"), get_user_balance))
    application.add_handler(MessageHandler(filters.Regex("Instructions"), get_instructions))
    application.add_handler(MessageHandler(filters.Regex("Share and Reward"), share_reward))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
