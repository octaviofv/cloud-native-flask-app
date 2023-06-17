from flask import Flask, jsonify
import requests
import random
app = Flask(__name__)

@app.route('/')
def get_quote():
    # Send a GET request to retrieve the list of genres
    response = requests.get('https://quote-garden.onrender.com/api/v3/genres')
    
    # Check if the request to fetch genres was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        # Extract the list of genres from the response
        genres = data['data']
        # Choose a random genre from the list
        random_genre = random.choice(genres)
    else:
        # Return an error JSON response if the request to fetch genres failed
        return jsonify(error='Failed to fetch genres')

    # Construct the URL with the random genre to fetch quotes
    quote_url = f"https://quote-garden.onrender.com/api/v3/quotes?genre={random_genre}"
    
    # Send a GET request to retrieve quotes for the random genre
    response = requests.get(quote_url)
    
    # Check if the request to fetch quotes was successful
    if response.status_code == 200:
        # Parse the JSON response
        quotes = response.json()['data']
        
        # Check if there are quotes available for the selected genre
        if len(quotes) > 0:
            # Choose a random quote from the list
            random_quote = random.choice(quotes)
            # Extract the quote, author, and genre from the selected quote
            quote_text = random_quote['quoteText']
            quote_author = random_quote['quoteAuthor']
            quote_genre = random_quote['quoteGenre']
            # Return the selected quote as a JSON response
            return jsonify(quote=quote_text, author=quote_author, genre=quote_genre)
        else:
            # Return an error JSON response if no quotes found for the genre
            return jsonify(error='No quotes found for the genre')
    else:
        # Return an error JSON response if the request to fetch quotes failed
        return jsonify(error='Failed to fetch quotes')

if __name__ == '__main__':
    app.run(debug=True, port=8000, host='0.0.0.0')