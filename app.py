#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
import json
import dateutil.parser
import babel
import sys
from flask import (
Flask, 
render_template, 
request, 
Response, 
flash, 
redirect, 
url_for, 
jsonify, 
abort
)
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form, FlaskForm
from forms import *
from flask_migrate import Migrate
import datetime


#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#
app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

#  Class State.
#  ----------------------------------------------------------------
class State(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(2), nullable=False, unique=True)
  cities = db.relationship('City', backref='state', lazy=True)
  venues = db.relationship('Venue', backref='state', lazy=True)
  artists = db.relationship('Artist', backref='state', lazy=True)

  def __repr__(self):
    return f'<id: {self.id} - {self.name}>'


#  Class City.
#  ----------------------------------------------------------------
class City(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(120), nullable=False)
  state_id = db.Column(db.Integer, db.ForeignKey('state.id'), nullable=False)  
  venues = db.relationship('Venue', backref="city", lazy=True)
  artists = db.relationship('Artist', backref="city", lazy=True)

  def __repr__(self):
    return f'<id: {self.id} - {self.name}>'


#  Class Venue.
#  ----------------------------------------------------------------
class Venue(db.Model):
  __tablename__ = 'Venue'

  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(), nullable=False, unique=True)
  city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
  state_id = db.Column(db.Integer, db.ForeignKey('state.id'), nullable=False)
  address = db.Column(db.String(120))
  phone = db.Column(db.String(120))
  image_link = db.Column(db.String(500))
  facebook_link = db.Column(db.String(120))
  seeking_talent = db.Column(db.Boolean, default=False)
  seeking_description= db.Column(db.String(120))
  website = db.Column(db.String(120))
  shows = db.relationship('Show', backref="venue", lazy=True)

  def __repr__(self):
    return f'<{self.name} / {self.state}>'

  def getListOfUpcomingShows(self):
    # Returns a list of upcoming shows in this venue
    today = self.getCurrentDate()
    all_shows = self.shows
    upcoming_shows = []
    for show in all_shows:
      if (show.start_time >= today):
        show_to_add = {}
        show_to_add['artist_id'] = show.artist_id
        show_to_add['artist_name'] = show.artist.name
        show_to_add['artist_image_link'] = show.artist.image_link
        show_to_add['venue_id'] = show.venue_id
        show_to_add['venue_name'] = show.venue.name
        show_to_add['start_time'] = show.start_time.strftime("%Y-%m-%d-T%H:%M:%S.000Z")
        upcoming_shows.append(show_to_add)
    return upcoming_shows     

  def getListOfPastShows(self):
    # Returns a list of past shows in this venue
    today = self.getCurrentDate()
    all_shows = self.shows
    past_shows = []
    for show in all_shows:
      if show.start_time <= today:
        show_to_add = {}
        show_to_add['artist_id'] = show.artist_id
        show_to_add['artist_name'] = show.artist.name
        show_to_add['artist_image_link'] = show.artist.image_link
        show_to_add['venue_id'] = show.venue_id
        show_to_add['venue_name'] = show.venue.name
        show_to_add['start_time'] = show.start_time.strftime("%Y-%m-%d-T%H:%M:%S.000Z")
        past_shows.append(show_to_add)
    return past_shows  

  @staticmethod
  def getCurrentDate():
    # Returns the current date as datetime
    current_date = datetime.datetime.today()
    return current_date  


#  Class Artist.
#  ----------------------------------------------------------------
class Artist(db.Model):
  __tablename__ = 'Artist'

  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String, nullable=False, unique=True)
  city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
  state_id = db.Column(db.Integer, db.ForeignKey('state.id'), nullable=False)
  phone = db.Column(db.String(120))
  image_link = db.Column(db.String(500))
  facebook_link = db.Column(db.String(120))
  website = db.Column(db.String(120))
  seeking_venues = db.Column(db.Boolean, nullable=False, default=False)
  seeking_description = db.Column(db.String())
  shows = db.relationship('Show', backref="artist", lazy="dynamic")

  def __repr__(self):
    return f'<Artist: {self.name} / City: {self.city}>'


#  Class Show.
#  ----------------------------------------------------------------
class Show(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
  artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
  start_time = db.Column(db.DateTime, nullable=False)

  def __repr__(self):
    return f'<Show at: {self.venue.name} / Artist: {self.artist.name} / Start Time: {self.start_time}>'


#  Class Genres
#  ----------------------------------------------------------------
class Genre(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(), nullable=False, unique=True)
  artists = db.relationship('Artist', secondary='genre_artist', lazy='subquery', 
    backref=db.backref('genres', lazy=True))
  venues = db.relationship('Venue', secondary='genre_venue', lazy='subquery',
    backref=db.backref('genres', lazy=True))
  
  def __repr__(self):
    return self.name
  

genre_artist = db.Table('genre_artist',
  db.Column('artist_id', db.Integer, db.ForeignKey('Artist.id'), primary_key=True),
  db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'), primary_key=True))

genre_venue = db.Table('genre_venue',
  db.Column('venue_id', db.Integer, db.ForeignKey('Venue.id'), primary_key=True),
  db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'), primary_key=True))

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en_US')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------
@app.route('/venues')
def venues():
  # displays list of venues at /venues
  error = False
  data = []
  try:
    cities = City.query.order_by(City.name).all()
    for city in cities:
      area = {}
      area['city'] = city.name
      area['state'] = city.state.name
      area['venues'] = []
      for venue in city.venues:
        venue_data = {}
        venue_data['id'] = venue.id
        venue_data['name'] = venue.name
        venue_data['num_upcoming_shows'] = len(venue.getListOfUpcomingShows())
        area['venues'].append(venue_data)
      area['venues'] = sorted(area['venues'], key=lambda i: i['name'])
      data.append(area)
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if error:
    abort(400)
  else:
    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term=request.form['search_term']
  query = Venue.query.filter(Venue.name.ilike('%' + str(search_term) + '%'))
  response={}
  data = []
  for venue in query.all():
    data.append(venue)
  response['count'] = query.count()
  response['data'] = data
  return render_template('pages/search_venues.html', results=response, search_term=search_term)


@app.route('/venues/<venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  error = False
  data = {}
  try:
    venue = Venue.query.get(venue_id)
    data['id'] = venue.id
    data['name'] = venue.name
    data['genres'] = venue.genres
    data['address'] = venue.address
    data['city'] = venue.city.name
    data['state'] = venue.state.name
    data['phone'] = venue.phone
    data['website'] = venue.website
    data['facebook_link'] = venue.facebook_link
    data['seeking_talent'] = venue.seeking_talent
    data['seeking_description'] = venue.seeking_description
    data['image_link'] = venue.image_link
    data['past_shows'] = venue.getListOfPastShows()
    data['upcoming_shows'] = venue.getListOfUpcomingShows()
    data['past_shows_count'] = len(venue.getListOfPastShows())
    data['upcoming_shows_count'] = len(venue.getListOfUpcomingShows())
  except:
    error = True
    print(sys.exc_info())
  if error:
    abort(400)
  else:
    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # called upon submitting the new venue listing form
  error = False
  try:
    #  get stateId from form
    state = request.form['state']
    state_in_table = State.query.filter_by(name=state)
    if (state_in_table.count() > 0):
      stateId = state_in_table.first().id
    else:
      new_state = State(name=state)
      db.session.add(new_state)
      db.session.commit()
      stateId = new_state.id
    #  get cityId from form
    city = request.form['city']
    city_in_table = City.query.filter_by(name=city) 
    if (city_in_table.count() > 0):
      cityId = city_in_table.first().id
    else:
      new_city = City(name = city, state_id = stateId)
      db.session.add(new_city)
      db.session.commit()
      cityId = new_city.id
    # Creates a new database entry
    new_venue = Venue(
      name=("%s" % request.form['name']),
      city_id= cityId,
      state_id = stateId,
      address = request.form['address'],
      phone = request.form['phone'],
      facebook_link = request.form['facebook_link']
    )
    db.session.add(new_venue)
    db.session.commit()
    # Adds the Genres to the new venue
    genres_to_add = request.form.getlist('genres')
    venue_added = Venue.query.order_by(Venue.id.desc()).first()
    for genre in genres_to_add:
      query = Genre.query.filter(Genre.name==genre).first()
      venue_added.genres.append(query)  
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()   
    venue = Venue.query.order_by(Venue.id.desc()).first()
  if error:
    abort(400)
    flash('An error ocurred. Venue ' + request.form['name'] + ' could not be listed.')
  else:
    flash('Venue ' + venue.name + ' was successfully listed!')
  return render_template('pages/home.html')


@app.route('/venues/delete/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    venue_to_delete = Venue.query.get(venue_id)
    db.session.delete(venue_to_delete)
    db.session.commit()
  except:
    db.session.rollback()
  finally:
    db.session.close()
  return jsonify({'success' : True})

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # displays an ordered list of artists at /artist
  error = False
  data=[]
  try: 
    all_artists = Artist.query.order_by(Artist.name).all()
    for artist in all_artists:
      artist_data = {}
      artist_data['id'] = artist.id
      artist_data['name'] = artist.name
      data.append(artist_data)
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if error:
    abort(400)
  else:
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term=request.form['search_term']
  query = Artist.query.filter(Artist.name.ilike('%' + str(search_term) + '%'))
  response={}
  data = []
  for venue in query.all():
    data.append(venue)
  response['count'] = query.count()
  response['data'] = data
  return render_template('pages/search_venues.html', results=response, search_term=search_term)


@app.route('/artists/<artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id
  error = False
  data = {}
  artist = Artist.query.get(artist_id)
  today = datetime.datetime.today()
  # generates a list of past shows
  past_shows = artist.shows.filter(Show.start_time <= today )
  list_of_past_shows = []
  for show in past_shows.all():
    show_info = {}
    show_info['venue_id'] = show.venue_id
    show_info['venue_name'] = show.venue.name
    show_info['venue_image_link'] = show.venue.image_link
    show_info['start_time'] = show.start_time.strftime("%Y-%m-%d-T%H:%M:%S.000Z")
    list_of_past_shows.append(show_info)
  # generates a list of upcoming shows
  upcoming_shows = artist.shows.filter(Show.start_time >= today)
  list_of_upcoming_shows = [] 
  for show in upcoming_shows.all():
    show_info = {}
    show_info['venue_id'] = show.venue_id
    show_info['venue_name'] = show.venue.name
    show_info['venue_image_link'] = show.venue.image_link
    show_info['start_time'] = show.start_time.strftime("%Y-%m-%d-T%H:%M:%S.000Z")
    list_of_upcoming_shows.append(show_info)
  try:
    data['id'] = artist.id
    data['name'] = artist.name
    data['genres'] = artist.genres 
    data['city'] = artist.city.name
    data['state'] = artist.state.name
    data['phone'] = artist.phone
    data['website'] = artist.website
    data['facebook_link'] = artist.facebook_link
    data['seeking_venue'] = artist.seeking_venues
    data['seeking_description'] = artist.seeking_description
    data['image_link'] = artist.image_link
    data['past_shows'] = list_of_past_shows
    data['past_shows_count'] = past_shows.count()
    data['upcoming_shows'] = list_of_upcoming_shows
    data['upcoming_shows_count'] = upcoming_shows.count()   
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if error:
    abort(400)
  else:
    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist={
    "id": 4,
    "name": "Guns N Petals",
    "genres": ["Rock n Roll"],
    "city": "San Francisco",
    "state": "CA",
    "phone": "326-123-5000",
    "website": "https://www.gunsnpetalsband.com",
    "facebook_link": "https://www.facebook.com/GunsNPetals",
    "seeking_venue": True,
    "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"
  }
  # TODO: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue={
    "id": 1,
    "name": "The Musical Hop",
    "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
    "address": "1015 Folsom Street",
    "city": "San Francisco",
    "state": "CA",
    "phone": "123-123-1234",
    "website": "https://www.themusicalhop.com",
    "facebook_link": "https://www.facebook.com/TheMusicalHop",
    "seeking_talent": True,
    "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
    "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60"
  }
  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)



@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  return redirect(url_for('show_venue', venue_id=venue_id))



#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  error = False
  try:
    #  get stateId 
    state = request.form['state']
    state_in_table = State.query.filter_by(name=state)
    if (state_in_table.count() > 0):
      stateId = state_in_table.first().id
    else:
      new_state = State(name=state)
      db.session.add(new_state)
      db.session.commit()
      stateId = new_state.id
    #  get cityId
    city = request.form['city']
    city_in_table = City.query.filter_by(name=city) 
    if (city_in_table.count() > 0):
      cityId = city_in_table.first().id
    else:
      new_city = City(name = city, state_id = stateId)
      db.session.add(new_city)
      db.session.commit()
      cityId = new_city.id
    # Creates a new database entry
    new_artist = Artist(
      name=("%s" % request.form['name']),
      city_id= cityId,
      state_id = stateId,
      phone = request.form['phone'],
      facebook_link = request.form['facebook_link']
    )
    db.session.add(new_artist)
    db.session.commit()
    # Adds the Genres to the new artist
    genres_to_add = request.form.getlist('genres')
    artist_added = Artist.query.order_by(Artist.id.desc()).first()
    for genre in genres_to_add:
      query = Genre.query.filter(Genre.name==genre).first()
      artist_added.genres.append(query)  
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()   
    artist = Artist.query.order_by(Artist.id.desc()).first()
  if error:
    abort(400)
    flash('An error ocurred. Artist ' + request.form['name'] + ' could not be listed.')
  else:
    flash('Artist ' + artist.name + ' was successfully listed!')
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  data=[]
  error = False
  try:
    upcoming_shows = Show.query.all()
    for show in upcoming_shows:
      show_data = {}
      show_data['venue_id'] = show.venue_id
      show_data['venue_name'] = show.venue.name
      show_data['artist_id'] = show.artist_id
      show_data['artist_name'] = show.artist.name
      show_data['artist_image_link'] = show.artist.image_link
      show_data['start_time'] = show.start_time.strftime("%Y-%m-%d-T%H:%M:%S.000Z")
      print(dateutil.parser.parse(show_data['start_time']))
      data.append(show_data)
    print(data)
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if error:
    abort(400)
  else:
    return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  error = False
  try: 
    artist_id = request.form['artist_id']
    venue_id = request.form['venue_id'] 
    check_artist = Artist.query.filter(Artist.id == artist_id).count()
    check_venue = Venue.query.filter(Venue.id == venue_id).count()
    if (check_artist > 0 and check_venue > 0):
      new_show = Show(
        venue_id = venue_id,
        artist_id = artist_id,
        start_time = dateutil.parser.parse(request.form['start_time'])
      )
      db.session.add(new_show)
      db.session.commit()
      flash_message = 'Show was successfully listed!'
    else:
      db.session.rollback()
      flash_message = 'Show was not listed. Check Venue and Artist Id.'
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if error:
    abort(400)
  else:
    flash(flash_message)
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
