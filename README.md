# Tele-Tracker Bot
A python telegram bot to help track daily expenses onto google sheet

## Getting Started (Users)
1. Access the bot on [telegram](https://t.me/telefinance_tracker_bot) 
2. Use the /start command and follow the instructions given.
3. Remember to edit the `Dropdown` sheet on Google Sheet to get started.
4. Happy using!

## Getting Started (Developers)
### Prerequisites
1. Set up Google Sheet API
2. Set up Firebase Realtime Database / or use SQLite3
3. Retrieve your service accounts for both Google Services and put it under the account folders as service_account.json & firebase_account.json
4. Retrieve your database url and set it under .env
5. Set up telegram bot via [BotFather](https://t.me/BotFather)
6. Retrieve your bot API token and set it under .env

### Installation
1. Clone the repo and run to get required dependencies
```python
pip install -r requirements.txt
```
2. Run
```python
python3 main.py
```

## Usage
/start - Start bot and configure your google sheet

/config - To update your google sheet, or configure quick settings for /addtransports and /addothers

/addentry - To add new entry

/addtranports - To quickly add new transport entry

/addothers - To quickly add others entry

/cancel - To cancel previous conversation with bot

## Pending feature
1. More options for /addothers
2. Use webhook instead of polling
3. Host onto serverless function

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<!-- CONTACT -->
## Contact

Bruce Wang: hello@brucewzj.com

LinkedIn: [https://www.linkedin.com/in/brucewzj/](https://www.linkedin.com/in/brucewzj/)

Project Link: [https://github.com/brucewzj99/tele-tracker](https://github.com/brucewzj99/tele-tracker)



