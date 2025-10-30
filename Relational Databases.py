# shop_database.py

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Part 1: Setup
engine = create_engine('sqlite:///shop.db', echo=True)  # echo=True shows SQL in console
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# Part 2: Define Tables
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    
    orders = relationship('Order', back_populates='user')
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Integer)
    
    orders = relationship('Order', back_populates='product')
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer)
    shipped = Column(Boolean, default=False)  # Bonus: status column
    
    user = relationship('User', back_populates='orders')
    product = relationship('Product', back_populates='orders')
    
    def __repr__(self):
        return (f"<Order(id={self.id}, user='{self.user.name}', "
                f"product='{self.product.name}', quantity={self.quantity}, shipped={self.shipped})>")

# Part 3: Create Tables
Base.metadata.create_all(engine)

# Part 4: Insert Data
# Add Users
user1 = User(name='Alice Johnson', email='alice@example.com')
user2 = User(name='Bob Smith', email='bob@example.com')

session.add_all([user1, user2])
session.commit()

# Add Products
product1 = Product(name='Laptop', price=1000)
product2 = Product(name='Smartphone', price=500)
product3 = Product(name='Headphones', price=150)

session.add_all([product1, product2, product3])
session.commit()

# Add Orders
order1 = Order(user=user1, product=product1, quantity=1, shipped=True)
order2 = Order(user=user1, product=product3, quantity=2)
order3 = Order(user=user2, product=product2, quantity=3)
order4 = Order(user=user2, product=product3, quantity=1)

session.add_all([order1, order2, order3, order4])
session.commit()

# Part 5: Queries
print("\n--- All Users ---")
for user in session.query(User).all():
    print(user)

print("\n--- All Products ---")
for product in session.query(Product).all():
    print(product)

print("\n--- All Orders ---")
for order in session.query(Order).all():
    print(f"User: {order.user.name}, Product: {order.product.name}, Quantity: {order.quantity}, Shipped: {order.shipped}")

# Update a product price
print("\n--- Updating Product Price ---")
product_to_update = session.query(Product).filter_by(name='Laptop').first()
print(f"Old Price: {product_to_update.price}")
product_to_update.price = 1200
session.commit()
print(f"New Price: {product_to_update.price}")

# Delete a user by ID
print("\n--- Deleting User with ID 2 ---")
user_to_delete = session.query(User).get(2)
if user_to_delete:
    session.delete(user_to_delete)
    session.commit()
    print("User deleted successfully")
else:
    print("User not found")

# Bonus: Query all orders not shipped
print("\n--- Orders Not Shipped ---")
for order in session.query(Order).filter_by(shipped=False):
    print(order)

# Bonus: Count total orders per user
print("\n--- Total Orders per User ---")
from sqlalchemy import func
order_counts = session.query(User.name, func.count(Order.id)).join(Order).group_by(User.id).all()
for name, count in order_counts:
    print(f"{name}: {count} orders")
