import os
import dash
import pandas as pd
import tweepy
import uuid
import requests
import plotly.express as px
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

hashtag = 'christmas'

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

subscription_key = os.environ.get('SUBSCRIPTION_KEY')
endpoint = os.environ.get('ENDPOINT')
bearer_token = os.environ.get('BEARER_TOKEN')

client = tweepy.Client(bearer_token)
query = f'#{hashtag} lang:en -is:retweet'

dash_app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app = dash_app.server
dash_app.layout = html.Div(
    html.Div([
        html.H4(f'Twitter Live Sentiment Analysis on {hashtag}'),
        html.Div(id='live-update-tweet'),
        dcc.Interval(
            id='interval-component',
            interval=10*1000,  # in milliseconds
            n_intervals=0
        )
    ])
)


def get_sentiment(texts, input_language='en'):
    path = '/text/analytics/v3.0/sentiment'
    constructed_url = endpoint + path

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    body = {
        'documents': [
            {
                'language': input_language,
                'id': i,
                'text': text
            }
            for i, text in enumerate(texts)]
    }
    response = requests.post(constructed_url, headers=headers, json=body)
    return response.json()


@dash_app.callback(Output('live-update-tweet', 'children'),
                   Input('interval-component', 'n_intervals'))
def update_metrics(n):
    tweets = client.search_recent_tweets(query)
    sentiments = get_sentiment([tweet.text for tweet in tweets.data])
    if not len(sentiments.get('documents', [])):
        return dash.no_update
    data = {}
    for sentiment in sentiments.get('documents', []):
        value = sentiment.get('sentiment')
        data[value] = data.setdefault(value, 0) + 1
    data = pd.DataFrame(data.items(), columns=['sentiment', 'tweets'])
    fig = px.histogram(data,
                       x='sentiment',
                       y='tweets',
                       range_y=[0, 10],
                       category_orders=dict(
                           sentiment=['positive', 'neutral', 'negative', 'mixed'])
                       )
    children = [dcc.Graph(figure=fig)]
    children.extend([
        html.Div([
            html.Div(
                [html.Span('Tweet: ', style={'font-weight': 'bold'}), html.Span(tweet.text)]),
            html.Div(
                [html.Span('Sentiment: ', style={'font-weight': 'bold'}), html.Span(sentiment.get('sentiment'))])
        ], style={'display': 'flex', 'flex-direction': 'column', 'padding': '5px'})
        for tweet, sentiment in zip(tweets.data, sentiments.get('documents', []))
    ])
    return children


if __name__ == '__main__':
    dash_app.run_server(debug=True)
