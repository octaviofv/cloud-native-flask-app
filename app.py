from flask import Flask, jsonify, render_template, session
import requests
import random
import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.route('/')
def random_quote_generator():
    # Render the 'index.html' template
    return render_template('index.html')

@app.route('/qotd')
def quote_of_the_day():
    # Get the quote of the day from the session
    quote_of_the_day = session.get('quote_of_the_day')

    # If the quote of the day is not stored in the session, fetch it
    if quote_of_the_day is None:
        quote_of_the_day = fetch_quote_of_the_day()
        session['quote_of_the_day'] = quote_of_the_day

    # Render the 'qotd.html' template with the quote of the day
    return render_template('qotd.html', quote_of_the_day=quote_of_the_day)

@app.route('/quote')
def get_quote():
    # Fetch the list of genres from the external API
    response = requests.get('https://quote-garden.onrender.com/api/v3/genres')

    if response.status_code == 200:
        data = response.json()
        genres = data['data']
        random_genre = random.choice(genres)
    else:
        return jsonify(error='Failed to fetch genres')

    # Fetch a random quote from the selected genre
    quote_url = f"https://quote-garden.onrender.com/api/v3/quotes?genre={random_genre}"
    response = requests.get(quote_url)

    if response.status_code == 200:
        quotes = response.json()['data']

        if len(quotes) > 0:
            random_quote = random.choice(quotes)
            quote_text = random_quote['quoteText']
            quote_author = random_quote['quoteAuthor']
            quote_genre = random_quote['quoteGenre']
            return jsonify(quote=quote_text, author=quote_author, genre=quote_genre)
        else:
            return jsonify(error='No quotes found for the genre')
    else:
        return jsonify(error='Failed to fetch quotes')

def fetch_quote_of_the_day():
    # Fetch the quote of the day for the current date from the external API
    current_date = datetime.date.today().strftime("%Y-%m-%d")
    quote_url = f"https://quote-garden.onrender.com/api/v3/quotes/random?date={current_date}"
    response = requests.get(quote_url)

    if response.status_code == 200:
        quote_data = response.json()['data']

        if len(quote_data) > 0:
            first_quote = quote_data[0]
            quote_text = first_quote['quoteText']
            quote_author = first_quote['quoteAuthor']
            quote_genre = first_quote['quoteGenre']
            return {
                'quote': quote_text,
                'author': quote_author,
                'genre': quote_genre
            }

    return None

if __name__ == '__main__':
    # Run the Flask application in debug mode on port 8000
    app.run(debug=True, port=8000, host='0.0.0.0')
