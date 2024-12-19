from sqlalchemy import func, create_engine
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import selectinload, sessionmaker

from app.models import User, Airport, FlightRoute, Flight, Company, Plane, Seat, FlightType
from app import db
import hashlib
import cloudinary.uploader
from datetime import datetime

def get_user_by_id(id):
    return User.query.get(id)


def auth_user(username, password, role = None):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    u = User.query.filter(User.username.__eq__(username.strip()),
                             User.password.__eq__(password))
    if role:
        u = u.filter(User.user_role.__eq__(role))

    return u.first()


def add_user(name, username, password, email, dob, gender, avatar):

    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    gender_bool = True

    if isinstance(dob, str):
        try:
            dob_obj = datetime.strptime(dob, '%Y-%m-%d')
            dob = dob_obj.strftime('%d-%m-%Y')
        except ValueError:
            raise ValueError("Ngày sinh không hợp lệ. Định dạng phải là YYYY-MM-DD.")
    u = User(name=name.strip(), username=username.strip(), password=password, email=email.strip(),dob=dob,gender=gender_bool)

    if avatar:
        res = cloudinary.uploader.upload(avatar)
        u.avatar = res.get('secure_url')

    db.session.add(u)
    db.session.commit()


def load_airports():
    return Airport.query.all()

def load_flight_routes():
    return FlightRoute.query.all()

def get_airport_by_id(id):
    return Airport.query.get(id)

def load_flights():
    return Flight.query.all()



def get_popular_routes(departure_name=None):

    arrival_airport = db.aliased(Airport)


    query = db.session.query(
        FlightRoute.fr_id,
        Airport.airport_name.label('departure'),
        arrival_airport.airport_name.label('arrival'),
        arrival_airport.airport_image.label('image'),
        FlightRoute.description
    ).join(
        Airport, FlightRoute.departure_airport_id == Airport.airport_id
    ).join(
        arrival_airport, FlightRoute.arrival_airport_id == arrival_airport.airport_id
    )

    if departure_name:
        query = query.filter(Airport.airport_address.ilike(f"%{departure_name}%"))

    return query.all()





def search_flights(departure, arrival, departure_date,total_needed_seats):
    # Tìm kiếm sân bay đi và đến
    departure_airport = Airport.query.filter_by(airport_name=departure).first()
    arrival_airport = Airport.query.filter_by(airport_name=arrival).first()

    if not departure_airport or not arrival_airport:
        return None, "Airport not found"

    # Lọc các tuyến bay từ sân bay đi đến sân bay đến
    flight_routes = FlightRoute.query.filter(
        FlightRoute.departure_airport_id == departure_airport.airport_id,
        FlightRoute.arrival_airport_id == arrival_airport.airport_id
    ).all()

    if not flight_routes:
        return [], None

    # Chuyển ngày đi thành định dạng đối tượng date
    departure_date_obj = datetime.strptime(departure_date, '%Y-%m-%d').date() if departure_date else None

    # Lọc chuyến bay theo tuyến bay và ngày đi
    flights = Flight.query.filter(
        Flight.flight_route_id.in_([route.fr_id for route in flight_routes]),
        func.date(Flight.f_dept_time) == departure_date_obj
    ).all()

    available_flights = []

    for flight in flights:
        available_economy_seats = flight.available_economy_seats()  # Số ghế ECONOMY còn lại
        available_business_seats = flight.available_business_seats()  # Số ghế BUSINESS còn lại

        # Kiểm tra nếu có đủ ghế cho hành khách
        if available_economy_seats >= total_needed_seats or available_business_seats >= total_needed_seats:
            available_flights.append(flight)

    return available_flights,None



