from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import fields, validates, ValidationError
from sqlalchemy import UniqueConstraint, DateTime
from datetime import datetime
import os

app = Flask(__name__)

# ---------- CONFIG ----------
# Replace <YOUR_PASSWORD> with your MySQL root password (or use another user)
DB_USER = os.getenv("ECO_DB_USER", "root")
DB_PASS = os.getenv("ECO_DB_PASS", "<YOUR_PASSWORD>")
DB_HOST = os.getenv("ECO_DB_HOST", "localhost")
DB_NAME = os.getenv("ECO_DB_NAME", "ecommerce_api")

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ---------- INIT ----------
db = SQLAlchemy(app)
ma = Marshmallow(app)

# ---------- MODELS ----------

# Association table for many-to-many relationship between Orders and Products
class OrderProduct(db.Model):
    __tablename__ = 'order_product'
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint('order_id', 'product_id', name='uq_order_product'),
    )

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(250))
    email = db.Column(db.String(150), unique=True, nullable=False)

    orders = db.relationship('Order', backref='user', cascade="all, delete-orphan")

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    products = db.relationship('Product', secondary='order_product', back_populates='orders')

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)

    orders = db.relationship('Order', secondary='order_product', back_populates='products')

# ---------- SCHEMAS ----------
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        include_fk = True
        sqla_session = db.session

    id = ma.auto_field(dump_only=True)
    name = ma.auto_field(required=True)
    email = ma.auto_field(required=True)
    address = ma.auto_field()

    @validates('email')
    def validate_email(self, value):
        if '@' not in value:
            raise ValidationError("Invalid email address")

class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        load_instance = True
        include_fk = True
        sqla_session = db.session

    id = ma.auto_field(dump_only=True)
    product_name = ma.auto_field(required=True)
    price = ma.auto_field(required=True)

    @validates('price')
    def validate_price(self, value):
        if value < 0:
            raise ValidationError("Price must be non-negative")


class OrderProductSchema(ma.Schema):
    order_id = fields.Int(required=True)
    product_id = fields.Int(required=True)
    quantity = fields.Int(missing=1)

class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        load_instance = True
        include_fk = True
        sqla_session = db.session

    id = ma.auto_field(dump_only=True)
    order_date = fields.DateTime(required=True)
    user_id = ma.auto_field(required=True)
    products = ma.Nested(ProductSchema, many=True, dump_only=True)


user_schema = UserSchema()
users_schema = UserSchema(many=True)

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

order_product_schema = OrderProductSchema()

# ---------- HELPERS ----------
def get_user_or_404(user_id):
    user = User.query.get(user_id)
    if not user:
        abort(404, description=f"User {user_id} not found")
    return user

def get_product_or_404(product_id):
    p = Product.query.get(product_id)
    if not p:
        abort(404, description=f"Product {product_id} not found")
    return p

def get_order_or_404(order_id):
    o = Order.query.get(order_id)
    if not o:
        abort(404, description=f"Order {order_id} not found")
    return o

# ---------- USER ENDPOINTS ----------
@app.route('/users', methods=['GET'])
def list_users():
    users = User.query.all()
    return jsonify(users_schema.dump(users)), 200

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = get_user_or_404(user_id)
    return jsonify(user_schema.dump(user)), 200

@app.route('/users', methods=['POST'])
def create_user():
    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input provided"}), 400

    # validation via schema (this will raise if invalid)
    try:
        data = user_schema.load(json_data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    # enforce unique email
    if User.query.filter_by(email=data.email).first():
        return jsonify({"message": "Email already in use"}), 400

    db.session.add(data)
    db.session.commit()
    return jsonify(user_schema.dump(data)), 201

@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = get_user_or_404(user_id)
    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input provided"}), 400

    # apply partial updates safely
    name = json_data.get("name")
    address = json_data.get("address")
    email = json_data.get("email")

    if email and email != user.email:
        if User.query.filter_by(email=email).first():
            return jsonify({"message": "Email already in use"}), 400
        user.email = email

    if name:
        user.name = name
    if address is not None:
        user.address = address

    db.session.commit()
    return jsonify(user_schema.dump(user)), 200

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = get_user_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"User {user_id} deleted"}), 200

# ---------- PRODUCT ENDPOINTS ----------
@app.route('/products', methods=['GET'])
def list_products():
    products = Product.query.all()
    return jsonify(products_schema.dump(products)), 200

@app.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    p = get_product_or_404(product_id)
    return jsonify(product_schema.dump(p)), 200

@app.route('/products', methods=['POST'])
def create_product():
    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input provided"}), 400

    try:
        data = product_schema.load(json_data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    db.session.add(data)
    db.session.commit()
    return jsonify(product_schema.dump(data)), 201

@app.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    p = get_product_or_404(product_id)
    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input provided"}), 400

    if 'product_name' in json_data:
        p.product_name = json_data['product_name']
    if 'price' in json_data:
        try:
            price_val = float(json_data['price'])
            if price_val < 0:
                return jsonify({"message": "Price must be non-negative"}), 400
            p.price = price_val
        except ValueError:
            return jsonify({"message": "Price must be numeric"}), 400

    db.session.commit()
    return jsonify(product_schema.dump(p)), 200

@app.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    p = get_product_or_404(product_id)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"message": f"Product {product_id} deleted"}), 200

# ---------- ORDER ENDPOINTS ----------
@app.route('/orders', methods=['POST'])
def create_order():
    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input provided"}), 400

    # Validate presence of user_id and order_date. order_date can be string that parses to datetime.
    user_id = json_data.get('user_id')
    order_date_raw = json_data.get('order_date')

    if not user_id:
        return jsonify({"message": "user_id is required"}), 400
    try:
        user = get_user_or_404(int(user_id))
    except ValueError:
        return jsonify({"message": "user_id must be integer"}), 400

    # parse order_date if provided, else use now
    if order_date_raw:
        try:
            # Accept ISO format
            order_date = datetime.fromisoformat(order_date_raw)
        except Exception:
            return jsonify({"message": "order_date must be ISO datetime string (e.g. 2023-03-01T12:00:00)"}), 400
    else:
        order_date = datetime.utcnow()

    order = Order(order_date=order_date, user_id=user.id)
    db.session.add(order)
    db.session.commit()
    return jsonify(order_schema.dump(order)), 201

@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods=['PUT'])
def add_product_to_order(order_id, product_id):
    order = get_order_or_404(order_id)
    product = get_product_or_404(product_id)

    # prevent duplicate
    assoc = OrderProduct.query.filter_by(order_id=order.id, product_id=product.id).first()
    if assoc:
        return jsonify({"message": "Product already in order"}), 400

    new_assoc = OrderProduct(order_id=order.id, product_id=product.id, quantity=1)
    db.session.add(new_assoc)
    db.session.commit()
    # refresh relationship
    db.session.refresh(order)
    return jsonify({"message": f"Product {product_id} added to order {order_id}"}), 200

@app.route('/orders/<int:order_id>/remove_product/<int:product_id>', methods=['DELETE'])
def remove_product_from_order(order_id, product_id):
    order = get_order_or_404(order_id)
    product = get_product_or_404(product_id)

    assoc = OrderProduct.query.filter_by(order_id=order.id, product_id=product.id).first()
    if not assoc:
        return jsonify({"message": "Product not found in order"}), 404

    db.session.delete(assoc)
    db.session.commit()
    return jsonify({"message": f"Product {product_id} removed from order {order_id}"}), 200

@app.route('/orders/user/<int:user_id>', methods=['GET'])
def get_orders_for_user(user_id):
    user = get_user_or_404(user_id)
    orders = Order.query.filter_by(user_id=user.id).all()
    return jsonify(orders_schema.dump(orders)), 200

@app.route('/orders/<int:order_id>/products', methods=['GET'])
def get_products_for_order(order_id):
    order = get_order_or_404(order_id)
    # return product list for the order
    prods = order.products
    return jsonify(products_schema.dump(prods)), 200

# ---------- ERROR HANDLERS ----------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"message": getattr(e, 'description', 'Resource not found')}), 404

@app.errorhandler(400)
def bad_request(e):
    return jsonify({"message": getattr(e, 'description', 'Bad request')}), 400

@app.errorhandler(500)
def server_error(e):
    return jsonify({"message": "An internal error occurred"}), 500

# ---------- DB CREATION ----------
@app.before_first_request
def create_tables():
    # create DB if not exists - MySQL must have the database created beforehand or you can create with workbench.
    # db.create_all() will create tables inside the configured database.
    db.create_all()

# ---------- RUN ----------
if __name__ == '__main__':
    # For development only - use gunicorn for production.
    app.run(debug=True, host='0.0.0.0', port=5000)
