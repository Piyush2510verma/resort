from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

def init_db():
    # Initialize the database and create tables if they don't exist
    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()

    # Table for room details
    cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        room_number TEXT NOT NULL UNIQUE,
                        is_booked INTEGER DEFAULT 0
                    )''')

    # Table for reservations
    cursor.execute('''CREATE TABLE IF NOT EXISTS reservations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guest_name TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        check_in_date TEXT NOT NULL,
                        check_out_date TEXT NOT NULL,
                        room_id INTEGER NOT NULL,
                        FOREIGN KEY (room_id) REFERENCES rooms (id)
                    )''')

    # Table for bills
    cursor.execute('''CREATE TABLE IF NOT EXISTS bills (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guest_name TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        room_number TEXT NOT NULL,
                        total_payment REAL NOT NULL
                    )''')

    # Table for housekeeping supplies
    cursor.execute('''CREATE TABLE IF NOT EXISTS supplies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_name TEXT NOT NULL,
                        quantity INTEGER NOT NULL
                    )''')

    # Table for food inventory
    cursor.execute('''CREATE TABLE IF NOT EXISTS food_inventory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_name TEXT NOT NULL,
                        quantity TEXT NOT NULL  -- Store quantity as string (e.g., "3kg")
                    )''')

    # Populate rooms (if not already populated)
    cursor.execute('SELECT COUNT(*) FROM rooms')
    if cursor.fetchone()[0] == 0:
        for room_number in range(101, 111):  # Example room numbers: 101-110
            cursor.execute('INSERT INTO rooms (room_number) VALUES (?)', (room_number,))

    conn.commit()
    conn.close()


@app.route('/')
def menu():
    # Display main menu options
    return render_template('menu.html')

@app.route('/book-room')
def book_room():
    # Show available rooms for booking
    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()
    cursor.execute('SELECT room_number FROM rooms WHERE is_booked = 0')
    available_rooms = cursor.fetchall()
    conn.close()

    return render_template('book_room.html', rooms=available_rooms)

@app.route('/book', methods=['POST'])
def book():
    # Handle room booking
    guest_name = request.form['guest_name']
    phone = request.form['phone']
    check_in_date = request.form['check_in_date']
    check_out_date = request.form['check_out_date']
    room_number = request.form['room_number']

    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()

    # Get the room ID
    cursor.execute('SELECT id FROM rooms WHERE room_number = ? AND is_booked = 0', (room_number,))
    room = cursor.fetchone()
    if not room:
        conn.close()
        return "Room not available or already booked.", 400

    room_id = room[0]

    # Insert reservation
    cursor.execute('''INSERT INTO reservations (guest_name, phone, check_in_date, check_out_date, room_id)
                      VALUES (?, ?, ?, ?, ?)''',
                   (guest_name, phone, check_in_date, check_out_date, room_id))

    # Mark room as booked
    cursor.execute('UPDATE rooms SET is_booked = 1 WHERE id = ?', (room_id,))

    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/checkout')
def checkout():
    # Show all reservations for checkout
    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT r.id, r.guest_name, r.phone, rm.room_number
                      FROM reservations r
                      JOIN rooms rm ON r.room_id = rm.id''')
    reservations = cursor.fetchall()

    conn.close()

    return render_template('checkout.html', reservations=reservations)

@app.route('/generate-bill', methods=['POST'])
def generate_bill():
    # Generate and save bill during checkout
    reservation_id = request.form['reservation_id']
    room_price = float(request.form['room_price'])
    food_charge = float(request.form['food_charge'])
    activities_charge = float(request.form['activities_charge'])

    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()

    # Get the reservation details
    cursor.execute('''SELECT r.guest_name, r.phone, rm.room_number, r.room_id
                      FROM reservations r
                      JOIN rooms rm ON r.room_id = rm.id
                      WHERE r.id = ?''', (reservation_id,))
    reservation = cursor.fetchone()
    if not reservation:
        conn.close()
        return "Invalid reservation ID.", 400

    guest_name, phone, room_number, room_id = reservation

    # Calculate total payment
    total_payment = room_price + food_charge + activities_charge

    # Insert bill into bills table
    cursor.execute('''INSERT INTO bills (guest_name, phone, room_number, total_payment)
                      VALUES (?, ?, ?, ?)''',
                   (guest_name, phone, room_number, total_payment))

    # Delete the reservation
    cursor.execute('DELETE FROM reservations WHERE id = ?', (reservation_id,))

    # Mark room as available
    cursor.execute('UPDATE rooms SET is_booked = 0 WHERE id = ?', (room_id,))

    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/supplies')
def supplies():
    # Show housekeeping supplies
    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, item_name, quantity FROM supplies')
    supplies = cursor.fetchall()
    conn.close()

    return render_template('supplies.html', supplies=supplies)

@app.route('/add-supply', methods=['POST'])
def add_supply():
    # Add a new housekeeping supply
    item_name = request.form['item_name']
    quantity = int(request.form['quantity'])

    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO supplies (item_name, quantity) VALUES (?, ?)', (item_name, quantity))
    conn.commit()
    conn.close()

    return redirect('/supplies')

@app.route('/update-supply/<int:supply_id>', methods=['POST'])
def update_supply(supply_id):
    # Update quantity of a housekeeping supply
    quantity = int(request.form['quantity'])

    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE supplies SET quantity = ? WHERE id = ?', (quantity, supply_id))
    conn.commit()
    conn.close()

    return redirect('/supplies')

@app.route('/delete-supply/<int:supply_id>', methods=['POST'])
def delete_supply(supply_id):
    # Delete a supply item from the database
    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM supplies WHERE id = ?', (supply_id,))
    
    conn.commit()
    conn.close()

    return redirect('/supplies')

@app.route('/food-inventory')
def food_inventory():
    # Show food inventory
    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, item_name, quantity FROM food_inventory')
    food_items = cursor.fetchall()
    conn.close()

    return render_template('food_inventory.html', food_items=food_items)

@app.route('/add-food-item', methods=['POST'])
def add_food_item():
    # Add a new food inventory item
    item_name = request.form['item_name']
    quantity = request.form['quantity']  # This will be a string like "3kg" or "5L"

    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO food_inventory (item_name, quantity) VALUES (?, ?)', (item_name, quantity))
    conn.commit()
    conn.close()

    return redirect('/food-inventory')


@app.route('/update-food-item/<int:food_id>', methods=['POST'])
def update_food_item(food_id):
    # Update the quantity of a food item
    quantity = int(request.form['quantity'])

    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE food_inventory SET quantity = ? WHERE id = ?', (quantity, food_id))
    conn.commit()
    conn.close()

    return redirect('/food-inventory')

@app.route('/delete-food-item/<int:food_id>', methods=['POST'])
def delete_food_item(food_id):
    # Delete a food item from the inventory
    conn = sqlite3.connect('rooms.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM food_inventory WHERE id = ?', (food_id,))
    conn.commit()
    conn.close()

    return redirect('/food-inventory')


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
