# Гайд по деплою
```
# Клонирование репозитория
apt update && apt upgrade -y && apt install -y git
git clone https://github.com/keyboardcrash1/binance-bot

# Создание виртуального окружения и установка библиотек
cd binance-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Редактирование .env (заполнение токена бота и chat_id для получателя)
nano .env

# Добавление правила в crontab
crontab -e # откроет редактор nano, в котором нужно будет добавить следующую строчку
*/5 * * * * /usr/bin/python3 /path/to/your/main.py
```
