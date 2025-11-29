import telebot
import requests
import jsons
from Class_ModelResponse import ModelResponse
from config import API_TOKEN, LM_STUDIO_URL

# Инициализация бота
bot = telebot.TeleBot(API_TOKEN)

# Словарь для хранения истории диалогов пользователей
user_histories = {}

def get_model_info():
    """Получение информации о модели из LM Studio"""
    try:
        response = requests.get(f'{LM_STUDIO_URL}/models', timeout=10)
        if response.status_code == 200:
            model_info = response.json()
            return model_info['data'][0]['id']
        return "Неизвестная модель"
    except:
        return "Не удалось получить информацию о модели"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    welcome_text = (
        "Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/model - показать используемую языковую модель\n"
        "/clear - очистить историю диалога\n\n"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['model'])
def send_model_name(message):
    """Обработчик команды /model"""
    model_name = get_model_info()
    bot.reply_to(message, f"Используемая модель: {model_name}")

@bot.message_handler(commands=['clear'])
def clear_history(message):
    """Обработчик команды /clear - очистка истории диалога"""
    user_id = message.from_user.id
    username = message.from_user.first_name
    
    if user_id in user_histories:
        user_histories[user_id] = []
        bot.reply_to(message, f"История диалога очищена.")
    else:
        bot.reply_to(message, f"Диалог пуст.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Обработчик всех текстовых сообщений"""
    user_id = message.from_user.id
    user_query = message.text
    
    # Инициализация истории для нового пользователя
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    # Добавляем системное сообщение при первом взаимодействии
    if len(user_histories[user_id]) == 0:
        user_histories[user_id].append({
            "role": "system",
            "content": "Ты полезный ассистент философ, который ёмко отвечает на вопросы пользователя."
        })
    
    # Добавляем запрос пользователя в историю
    user_histories[user_id].append({
        "role": "user",
        "content": user_query
    })
    
    # Формируем запрос с полной историей диалога
    request = {
        "messages": user_histories[user_id],
        "max_tokens": 500, #Ограничиваем длину ответа
        "temperature": 0.7
    }
    
    try:
        # Отправляем запрос к LM Studio
        response = requests.post(
            f'{LM_STUDIO_URL}/chat/completions',
            json=request,
            timeout=30
        )

        if response.status_code == 200:
            model_response = jsons.loads(response.text, ModelResponse)
            assistant_response = model_response.choices[0].message.content
            
            # Добавляем ответ ассистента в историю
            user_histories[user_id].append({
                "role": "assistant", 
                "content": assistant_response
            })
            
            bot.reply_to(message, assistant_response)
        else:
            # Если произошла ошибка, удаляем последний запрос пользователя из истории
            user_histories[user_id].pop()
            bot.reply_to(message, 'Произошла ошибка при обращении к модели. Попробуйте еще раз.')
            
    except requests.exceptions.ConnectionError:
        user_histories[user_id].pop()
        bot.reply_to(message, 'Не удалось подключиться к LM Studio. Убедитесь, что сервер запущен.')
    except Exception as e:
        user_histories[user_id].pop()
        bot.reply_to(message, f'Произошла непредвиденная ошибка: {str(e)}')

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)