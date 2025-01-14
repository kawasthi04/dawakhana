import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
from PIL import Image  # For handling images
import pytesseract  # For OCR

# Initialize the database
def init_db():
    conn = sqlite3.connect('pharmacy.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS customers 
                 (customer_id INTEGER PRIMARY KEY, name TEXT, contact TEXT, address TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS medicines 
                 (medicine_id INTEGER PRIMARY KEY, name TEXT, stock INTEGER, expiry_date TEXT, price REAL, info TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id INTEGER PRIMARY KEY, order_date TEXT, customer_id INTEGER, drug_id INTEGER, quantity INTEGER, total_amount REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)''')
    conn.commit()
    conn.close()

# Call the function to ensure the database is initialized
init_db()

# Global Layout Config
st.set_page_config(page_title="DawaKhana", layout="wide", page_icon="💊")

# Utility: Database Connection
def connect_db():
    return sqlite3.connect('pharmacy.db', check_same_thread=False)

# Utility: Logout Function
def logout():
    st.session_state.clear()
    st.success("Logged out successfully!")
    st.query_params.clear()  # Clear query parameters

# Function to extract text from an image using OCR
def extract_text_from_image(image):
    # Path to Tesseract executable (update if needed)
    pytesseract.pytesseract.tesseract_cmd = r"C:\Users\kusha\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
    
    # Perform OCR on the image
    text = pytesseract.image_to_string(image)
    return text

# Login Screen with Sign-Up Option
def login():
    st.title("DawaKhana 💊")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("static/green_bottle.svg", caption="The ultimate dispensary manager!", width=350)
    with col2:
        # Check if the user is in sign-up mode
        if 'sign_up_mode' not in st.session_state:
            st.session_state.sign_up_mode = False

        if st.session_state.sign_up_mode:
            # Sign-Up Section
            st.subheader("Sign Up")
            with st.form("sign_up_form"):
                new_username = st.text_input("Choose a Username")
                new_password = st.text_input("Choose a Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")

                if st.form_submit_button("Sign Up"):
                    if new_password != confirm_password:
                        st.error("Passwords do not match. Please try again.")
                    else:
                        conn = connect_db()
                        c = conn.cursor()
                        try:
                            # Check if the username already exists
                            c.execute("SELECT * FROM users WHERE username = ?", (new_username,))
                            if c.fetchone():
                                st.error("Username already exists. Please choose a different username.")
                            else:
                                # Insert the new user into the database
                                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                                          (new_username, new_password, 'customer'))
                                conn.commit()
                                st.success(f"User '{new_username}' registered successfully! Please login.")
                                st.session_state.sign_up_mode = False  # Switch back to login mode
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error during sign-up: {e}")
                        finally:
                            conn.close()

            # Back to Login Button (outside the form)
            if st.button("← Back"):
                st.session_state.sign_up_mode = False
                st.rerun()
        else:
            # Login Section
            st.subheader("Login")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")

                if st.form_submit_button("Login"):
                    conn = connect_db()
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
                    user = c.fetchone()
                    conn.close()

                    if user:
                        st.session_state['username'] = username
                        st.session_state['user_id'] = user[0]
                        st.session_state['role'] = user[3]
                        st.success(f"Welcome, {st.session_state['username']}!")
                        st.rerun()  # Rerun the app to reflect the new session state
                    else:
                        st.error("Invalid credentials. Please try again.")

            # Sign Up Button (outside the form)
            if st.button("Sign Up"):
                st.session_state.sign_up_mode = True
                st.rerun()

# Admin Dashboard
def admin_dashboard():
    st.sidebar.header("Admin Menu")
    st.sidebar.button("Logout", on_click=logout)

    menu_options = ["Dashboard", "Manage Drugs", "Add Drug", "Manage Users", "View Orders", "Reports"]
    selected_option = st.sidebar.radio("Navigate", menu_options)

    if 'username' in st.session_state:
        username = st.session_state['username']
        st.title(f"{username}'s Dashboard")
    st.markdown("---")
    
    if selected_option == "Dashboard":
        st.write("Welcome to the Admin Dashboard!")
    elif selected_option == "Manage Drugs":
        view_drugs()
    elif selected_option == "Add Drug":
        add_drug()
    elif selected_option == "Manage Users":
        manage_users()
    elif selected_option == "View Orders":
        view_orders()
    elif selected_option == "Reports":
        st.subheader("Reports Section (Coming Soon)")

# Display Drugs in a Structured Grid
def display_drugs_grid(drugs):
    cols_per_row = 4  # Number of columns per row
    cols = st.columns(cols_per_row)  # Create columns for the grid

    for idx, drug in enumerate(drugs):
        with cols[idx % cols_per_row]:
            # Card-like layout for each drug
            with st.container():
                st.image("static/bottle_blue.svg", caption=drug[1], width=100)  
                st.write(f"**Price:** ₹{drug[4]:.2f}")
                st.write(f"**Stock:** {drug[2]}")
                st.write(f"**Expiry:** {drug[3]}")
                if st.session_state['role'] == 'customer':
                    quantity = st.number_input(f"Quantity for {drug[1]}", min_value=1, step=1, key=f"qty_{drug[0]}")
                    if st.button(f"Buy {drug[1]}", key=f"buy_{drug[0]}"):
                        place_order(drug[0], quantity)
                st.markdown("---")

# Place Order Function
def place_order(drug_id, quantity):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT stock, price FROM medicines WHERE medicine_id = ?", (drug_id,))
    drug_info = c.fetchone()

    if drug_info and drug_info[0] >= quantity:
        total_amount = drug_info[1] * quantity
        c.execute("INSERT INTO orders (order_date, customer_id, drug_id, quantity, total_amount) VALUES (?, ?, ?, ?, ?)",
                  (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), st.session_state['user_id'], drug_id, quantity, total_amount))
        c.execute("UPDATE medicines SET stock = stock - ? WHERE medicine_id = ?", (quantity, drug_id))
        conn.commit()
        st.success(f"Order for {drug_id} placed successfully!")
    else:
        st.error("Insufficient stock.")
    conn.close()

# View Drugs
def view_drugs():
    st.subheader("Manage Drugs")
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT * FROM medicines")
    drugs = c.fetchall()
    conn.close()

    display_drugs_grid(drugs)

# Add Drug
def add_drug():
    st.subheader("Add New Drug")
    with st.form("add_drug_form"):
        name = st.text_input("Drug Name")
        stock = st.number_input("Stock Quantity", min_value=0, step=1)
        expiry_date = st.date_input("Expiry Date")
        price = st.number_input("Price (₹)", min_value=0.0, format="%.2f")
        info = st.text_area("Additional Information")

        if st.form_submit_button("Add Drug"):
            conn = connect_db()
            c = conn.cursor()
            c.execute("INSERT INTO medicines (name, stock, expiry_date, price, info) VALUES (?, ?, ?, ?, ?)", 
                      (name, stock, expiry_date.strftime('%Y-%m-%d'), price, info))
            conn.commit()
            conn.close()
            st.success("Drug added successfully!")

# Manage Users
def manage_users():
    st.subheader("Add a User")
    with st.form("add_user_form"):
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        new_role = st.selectbox("Role", ["admin", "customer"])

        if st.form_submit_button("Add User"):
            conn = connect_db()
            c = conn.cursor()
            try:
                c.execute("SELECT * FROM users WHERE username = ?", (new_username,))
                if c.fetchone():
                    st.error("Username already exists. Please choose a different username.")
                else:
                    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                              (new_username, new_password, new_role))
                    conn.commit()
                    st.success(f"User '{new_username}' added successfully!")
            except Exception as e:
                st.error(f"Error adding user: {e}")
            finally:
                conn.close()

    st.subheader("Remove a User")
    with st.form("remove_user_form"):
        user_id_to_remove = st.number_input("Enter User ID to Remove", min_value=1, step=1)
        if st.form_submit_button("Remove User"):
            conn = connect_db()
            c = conn.cursor()
            try:
                c.execute("DELETE FROM users WHERE user_id = ?", (user_id_to_remove,))
                conn.commit()
                st.success(f"User with ID {user_id_to_remove} removed successfully!")
            except Exception as e:
                st.error(f"Error removing user: {e}")
            finally:
                conn.close()
            st.rerun()

    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()

    if users:
        users_df = pd.DataFrame(users, columns=["ID", "Username", "Password", "Role"])
        st.dataframe(users_df, use_container_width=True)
    else:
        st.write("No users found.")

# View Orders
def view_orders():
    st.subheader("View Orders")
    conn = connect_db()
    c = conn.cursor()
    c.execute("""
        SELECT orders.order_id, orders.order_date, medicines.name, orders.quantity, orders.total_amount 
        FROM orders 
        JOIN medicines ON orders.drug_id = medicines.medicine_id
    """)
    orders = c.fetchall()
    conn.close()

    orders_df = pd.DataFrame(orders, columns=["Order ID", "Order Date", "Drug Name", "Quantity", "Total Amount"])
    st.dataframe(orders_df, use_container_width=True)

# Customer Dashboard
def customer_dashboard():
    st.sidebar.image("static/pills_bottle_logo.svg")
    st.sidebar.header("Customer Menu")
    st.sidebar.button("Logout", on_click=logout)

    menu_options = ["Buy Drugs", "Order History", "Search Drugs", "Upload Prescription"]
    selected_option = st.sidebar.radio("Navigate", menu_options)

    if 'username' in st.session_state:
        username = st.session_state['username']
        st.title(f"{username}'s Dashboard")
    st.markdown("---")
    
    if selected_option == "Buy Drugs":
        buy_drugs()
    elif selected_option == "Order History":
        view_order_history()
    elif selected_option == "Search Drugs":
        search_drugs()
    elif selected_option == "Upload Prescription":
        upload_prescription()

# Upload Prescription and Extract Text
def upload_prescription():
    st.subheader("Upload Prescription")
    uploaded_file = st.file_uploader("Upload an image of your prescription", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        # Display the uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Prescription", use_container_width=True)  # Updated parameter

        # Extract text from the image
        st.write("Extracting text from the image...")
        extracted_text = extract_text_from_image(image)

        # Display the extracted text
        st.subheader("Extracted Text")
        st.write(extracted_text)

# Buy Drugs
def buy_drugs():
    st.subheader("Available Drugs")
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT * FROM medicines")
    drugs = c.fetchall()
    conn.close()

    display_drugs_grid(drugs)

# View Order History
def view_order_history():
    st.subheader("Order History")
    conn = connect_db()
    c = conn.cursor()
    c.execute("""
        SELECT orders.order_id, orders.order_date, medicines.name, orders.quantity, orders.total_amount 
        FROM orders 
        JOIN medicines ON orders.drug_id = medicines.medicine_id 
        WHERE orders.customer_id = ?
    """, (st.session_state['user_id'],))
    orders = c.fetchall()
    conn.close()

    orders_df = pd.DataFrame(orders, columns=["Order ID", "Order Date", "Drug Name", "Quantity", "Total Amount"])
    st.dataframe(orders_df, use_container_width=True)

# Search Drugs
def search_drugs():
    st.subheader("Search Drugs")
    search_query = st.text_input("Enter drug names (comma-separated)")
    if st.button("Search"):
        drug_names = [name.strip() for name in search_query.split(',')]
        conn = connect_db()
        c = conn.cursor()
        query = f"SELECT * FROM medicines WHERE name IN ({','.join(['?'] * len(drug_names))})"
        c.execute(query, drug_names)
        results = c.fetchall()
        conn.close()

        if results:
            st.subheader("Search Results")
            display_drugs_grid(results)
        else:
            st.error("No matching drugs found.")

# Main Logic
if 'user_id' not in st.session_state:
    login()
else:
    if st.session_state['role'] == 'admin':
        admin_dashboard()
    else:
        customer_dashboard()
