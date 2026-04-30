"""FSM состояния."""

from aiogram.fsm.state import State, StatesGroup


class CheckoutSG(StatesGroup):
    waiting_address = State()        # data: {city_ids_pending: [int], addresses: {city_id: str}}
    waiting_method = State()
    waiting_txid = State()           # data: {payment_id: int}


class TopupSG(StatesGroup):
    waiting_amount = State()
    waiting_method = State()         # data: {amount}
    waiting_txid = State()           # data: {payment_id}


class ChatSG(StatesGroup):
    in_chat = State()                # data: {order_id}


class DisputeChatSG(StatesGroup):
    waiting_reason = State()         # data: {order_id}
    in_chat = State()                # data: {dispute_id}


class ReviewSG(StatesGroup):
    waiting_rating = State()
    waiting_text = State()           # data: {rating, order_id?}


# ---------- Админ-панель ----------


class AdminCitySG(StatesGroup):
    waiting_name = State()
    waiting_delivery_price = State()  # data: {name}


class AdminProductSG(StatesGroup):
    waiting_name = State()            # data: {city_id}
    waiting_description = State()
    waiting_photo = State()
    waiting_price = State()
    waiting_stock = State()


class AdminCourierSG(StatesGroup):
    waiting_user_id = State()         # data: {city_id}


class AdminFreeCreditsSG(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()          # data: {target_id}
