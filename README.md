# zora-analytics
NFT analytics on top of the Zora API...

The project leverages [Dash](https://plotly.com/dash/) for the visualisations, [Zora's GraphQL API](https://docs.zora.co/docs/zora-api/intro) for data and is deployed on Heroku.

See an example here:
↗ [HeyChris likes Zora](https://heychris-likes-zora.herokuapp.com/)

## Project structure
`app.py` where the dash app lives
`requirements.txt` key Python modules
`runtime.txt` simply tells Heroku (the Gunicorn HTTP server) which Python version to use
`Procfile` tells Heroku what type of process is going to run (Gunicorn web process) and the Python app entrypoint (app.py)
`/assets` stores favicon and stylesheet

## Get going
1. Clone repo
2. Install modules
    2. `pip3 install -r requirements.txt` or `conda install --file requirements.txt` (for Anaconda users)
3. Run the app
    3. `python app.py`
4. Setup Heroku CLI
    4. Here's [their guide](https://devcenter.heroku.com/articles/heroku-cli)
5. Login and create your Heroku app
    5. Run `heroku login`
    5. Run `heroku create {app_name}`
6. Deploy your app to Heroku
    6. `git push heroku main`
7. View app on Heroku
    7. It should be viewable at `{app-name}.herokuapp.com/`