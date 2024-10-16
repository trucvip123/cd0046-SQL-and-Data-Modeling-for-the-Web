# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
import logging
import sys
from logging import FileHandler, Formatter

import babel
import dateutil.parser
from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, url_for)
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import Form
from sqlalchemy.orm import joinedload

from common.models import Artist, Show, Venue, db
from common.utils import convert_genres
from forms import *

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object("config")

# Initialize the app with SQLAlchemy
db.init_app(app)

with app.app_context():
    db.create_all()

migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format="medium"):
    # If value is already a datetime object, no need to parse
    if isinstance(value, str):
        try:
            date = dateutil.parser.parse(value)
        except ValueError:
            raise TypeError(f"Unable to parse the date string: {value}")
    elif isinstance(value, datetime):
        date = value
    else:
        raise TypeError(f"Expected a string or datetime object, got {type(value)}")

    # Set format strings
    if format == "full":
        format = "EEEE MMMM d, y 'at' h:mma"
    elif format == "medium":
        format = "EEE MMM d, y h:mma"

    # Format the datetime using Babel
    return babel.dates.format_datetime(date, format, locale="en")


app.jinja_env.filters["datetime"] = format_datetime

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route("/")
def index():
    return render_template("pages/home.html")


#  Venues
#  ----------------------------------------------------------------


@app.route("/venues")
def venues():
    data = []
    current_time = datetime.now()  # Make this timezone aware if needed

    # Get all venues with related shows
    venueLocList = (
        Venue.query.distinct(Venue.state, Venue.city)
        .options(joinedload(Venue.shows))  # Eager load shows to avoid N+1 queries
        .all()
    )

    for venueLocation in venueLocList:
        city = venueLocation.city
        state = venueLocation.state

        venues = []

        venueList = Venue.query.filter_by(city=city, state=state).all()

        for venue in venueList:
            # Get upcoming shows directly from the database
            upcomingShowsCount = Show.query.filter(
                Show.venue_id == venue.id, Show.start_time > current_time
            ).count()

            venues.append(
                {
                    "id": venue.id,
                    "name": venue.name,
                    "num_upcoming_shows": upcomingShowsCount,
                }
            )

        data.append({"city": city, "state": state, "venues": venues})

    return render_template("pages/venues.html", areas=data)


@app.route("/venues/search", methods=["POST"])
def search_venues():
    searchTerm = request.form.get("search_term", "")

    venues = Venue.query.filter(Venue.name.ilike("%" + searchTerm + "%")).all()

    data = []
    current_time = datetime.now()

    for venue in venues:
        upcomingShows = list(
            filter(lambda show: show.start_time > current_time, venue.shows)
        )
        data.append(
            {
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": len(upcomingShows),
            }
        )

    result = {"count": len(venues), "data": data}

    return render_template(
        "pages/search_venues.html", results=result, search_term=searchTerm
    )


@app.route("/venues/<int:venue_id>")
def show_venue(venue_id):
    error = False
    data = {}

    try:

        venue = Venue.query.filter_by(id=venue_id).first()
        genres_list = convert_genres(venue.genres)

        data["id"] = venue.id
        data["name"] = venue.name
        data["city"] = venue.city
        data["state"] = venue.state
        data["address"] = venue.address
        data["phone"] = venue.phone
        data["genres"] = genres_list
        data["image_link"] = venue.image_link
        data["facebook_link"] = venue.facebook_link
        data["website"] = venue.website_link
        data["seeking_talent"] = venue.seeking_talent
        data["seeking_description"] = venue.seeking_description

        past_shows = []
        upcoming_shows = []
        current_time = datetime.now()

        artistShows = (
            db.session.query(
                Show.artist_id, Artist.name, Artist.image_link, Show.start_time
            )
            .filter_by(venue_id=venue.id)
            .join(Artist)
            .all()
        )

        for artistShow in artistShows:
            artistId, artistName, artistImgLink, showtime = artistShow
            artistShowRecord = {
                "artist_id": artistId,
                "artist_name": artistName,
                "artist_image_link": artistImgLink,
                "start_time": showtime,
            }
            if showtime > current_time:
                upcoming_shows.append(artistShowRecord)
            else:
                past_shows.append(artistShowRecord)

        data["past_shows"] = past_shows
        data["upcoming_shows"] = upcoming_shows

        data["past_shows_count"] = len(past_shows)
        data["upcoming_shows_count"] = len(upcoming_shows)
    except:
        error = True
        print(sys.exc_info())
    if error:
        # e.g., on unsuccessful db query, flash an error instead.
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
        flash("An error occurred. Venue id " + str(venue_id) + " not found.")
        abort(404)
    else:
        print("data:", data)
        return render_template("pages/show_venue.html", venue=data)


#  Create Venue
#  ----------------------------------------------------------------


@app.route("/venues/create", methods=["GET"])
def create_venue_form():
    form = VenueForm()
    return render_template("forms/new_venue.html", form=form)


@app.route("/venues/create", methods=["POST"])
def create_venue_submission():
    error = False
    form = VenueForm(request.form)
    try:
        venue = Venue(genres=form.genres.data)
        form.populate_obj(venue)
        db.session.add(venue)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        # e.g., on unsuccessful db insert, flash an error instead.
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
        flash("An error occurred. Venue " + form.name.data + " could not be listed.")
        abort(500)
    else:
        # on successful db insert, flash success
        flash("Venue " + form.name.data + " was successfully listed!")
        return render_template("pages/home.html")


@app.route("/venues/<int:venue_id>/delete", methods=["GET"])
def delete_venue(venue_id):
    error = False
    try:
        venue = Venue.query.get(venue_id)

        db.session.delete(venue)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        # e.g., on unsuccessful db delete, flash an error instead.
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
        flash("An error occurred. Venue " + str(venue_id) + " not found.")
        abort(404)
    else:
        # on successful db delete, flash success
        flash("Venue " + str(venue_id) + " was successfully deleted!")
        return render_template("pages/home.html")


#  Artists
#  ----------------------------------------------------------------
@app.route("/artists")
def artists():
    return render_template(
        "pages/artists.html", artists=Artist.query.order_by("id").all()
    )


@app.route("/artists/search", methods=["POST"])
def search_artists():
    searchTerm = request.form.get("search_term", "")

    artists = Artist.query.filter(Artist.name.ilike("%" + searchTerm + "%")).all()

    data = []
    current_time = datetime.now()

    for artist in artists:
        upcomingShows = list(
            filter(lambda show: show.start_time > current_time, artist.shows)
        )
        data.append(
            {
                "id": artist.id,
                "name": artist.name,
                "num_upcoming_shows": len(upcomingShows),
            }
        )

    result = {"count": len(artists), "data": data}

    return render_template(
        "pages/search_artists.html", results=result, search_term=searchTerm
    )


@app.route("/artists/<int:artist_id>")
def show_artist(artist_id):
    error = False
    data = {}

    try:
        artist = Artist.query.filter_by(id=artist_id).first()
        genres_list = convert_genres(artist.genres)

        data["id"] = artist.id
        data["name"] = artist.name
        data["city"] = artist.city
        data["state"] = artist.state
        data["phone"] = artist.phone
        data["genres"] = genres_list
        data["image_link"] = artist.image_link
        data["facebook_link"] = artist.facebook_link
        data["website"] = artist.website_link
        data["seeking_venue"] = artist.seeking_venue
        data["seeking_description"] = artist.seeking_description

        past_shows = []
        upcoming_shows = []
        current_time = datetime.now()

        venueShows = (
            db.session.query(
                Show.venue_id, Venue.name, Venue.image_link, Show.start_time
            )
            .filter_by(artist_id=artist.id)
            .join(Venue)
            .all()
        )

        for venueShow in venueShows:
            venueId, venueName, venueImgLink, showtime = venueShow
            venueShowRecord = {
                "venue_id": venueId,
                "venue_name": venueName,
                "venue_image_link": venueImgLink,
                "start_time": showtime,
            }
            if showtime > current_time:
                upcoming_shows.append(venueShowRecord)
            else:
                past_shows.append(venueShowRecord)

        data["past_shows"] = past_shows
        data["upcoming_shows"] = upcoming_shows

        data["past_shows_count"] = len(past_shows)
        data["upcoming_shows_count"] = len(upcoming_shows)
    except:
        error = True
        print(sys.exc_info())
    if error:
        # e.g., on unsuccessful db query, flash an error instead.
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
        flash("An error occurred. Artist id " + str(artist_id) + " not found.")
        abort(404)
    else:
        return render_template("pages/show_artist.html", artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route("/artists/<int:artist_id>/edit", methods=["GET"])
def edit_artist(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    form = ArtistForm(obj=artist)
    return render_template("forms/edit_artist.html", form=form, artist=artist)


@app.route("/artists/<int:artist_id>/edit", methods=["POST"])
def edit_artist_submission(artist_id):
    error = False
    form = ArtistForm(request.form)
    try:
        artist = Artist.query.get(artist_id)
        form.populate_obj(artist)
        db.session.add(artist)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        # e.g., on unsuccessful db update, flash an error instead.
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
        flash("An error occurred. Artist " + str(artist_id) + " not found.")
        abort(404)
    else:
        # on successful db update, flash success
        flash("Artist " + form.name.data + " was successfully updated!")
        return redirect(url_for("show_artist", artist_id=artist_id))


@app.route("/venues/<int:venue_id>/edit", methods=["GET"])
def edit_venue(venue_id):
    venue = Venue.query.get_or_404(venue_id)
    form = VenueForm(obj=venue)
    return render_template("forms/edit_venue.html", form=form, venue=venue)


@app.route("/venues/<int:venue_id>/edit", methods=["POST"])
def edit_venue_submission(venue_id):
    error = False
    form = VenueForm(request.form)
    try:
        venue = Venue.query.get(venue_id)
        form.populate_obj(venue)
        db.session.add(venue)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        # e.g., on unsuccessful db update, flash an error instead.
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
        flash("An error occurred. Venue " + str(venue_id) + " not found.")
        abort(404)
    else:
        # on successful db update, flash success
        flash("Venue " + form.name.data + " was successfully updated!")
        return redirect(url_for("show_venue", venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------


@app.route("/artists/create", methods=["GET"])
def create_artist_form():
    form = ArtistForm()
    return render_template("forms/new_artist.html", form=form)


@app.route("/artists/create", methods=["POST"])
def create_artist_submission():
    error = False
    form = ArtistForm(request.form)
    try:
        artist = Artist()
        form.populate_obj(artist)
        db.session.add(artist)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        # e.g., on unsuccessful db insert, flash an error instead.
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
        flash("An error occurred. Artist " + form.name.data + " could not be listed.")
        abort(500)
    else:
        # on successful db insert, flash success
        flash("Artist " + form.name.data + " was successfully listed!")
        return render_template("pages/home.html")


#  Shows
#  ----------------------------------------------------------------


@app.route("/shows")
def shows():
    data = []

    # Query to join Show with Venue and Artist
    shows = (
        db.session.query(
            Show.venue_id,
            Show.artist_id,
            Show.start_time,
            Venue.name.label("venue_name"),
            Artist.name.label("artist_name"),
            Artist.image_link.label("artist_image_link"),
        )
        .join(Venue, Show.venue_id == Venue.id)
        .join(Artist, Show.artist_id == Artist.id)
        .all()
    )

    for show in shows:
        venue_id, artist_id, start_time, venue_name, artist_name, artist_image_link = (
            show
        )
        data.append(
            {
                "venue_id": venue_id,
                "venue_name": venue_name,
                "artist_id": artist_id,
                "artist_name": artist_name,
                "artist_image_link": artist_image_link,
                "start_time": start_time,
            }
        )

    return render_template("pages/shows.html", shows=data)


@app.route("/shows/create")
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template("forms/new_show.html", form=form)


@app.route("/shows/create", methods=["POST"])
def create_show_submission():
    error = False
    form = ShowForm(request.form)
    print("form:", request.form)
    try:
        show = Show()
        form.populate_obj(show)
        db.session.add(show)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        # e.g., on unsuccessful db insert, flash an error instead.
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
        flash("An error occurred. Show could not be listed.")
        abort(500)
    else:
        # on successful db insert, flash success
        flash("Show was successfully listed!")
        return render_template("pages/home.html")


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


if not app.debug:
    file_handler = FileHandler("error.log")
    file_handler.setFormatter(
        Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info("errors")

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#
# Ensure tables are created
with app.app_context():
    db.create_all()  # This will create all tables if they don't exist

if __name__ == "__main__":
    app.run(debug=True)
