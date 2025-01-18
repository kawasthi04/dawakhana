import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
from PIL import Image  # For handling images
from text_extraction import extract_text_from_image, extract_entities  # Import OCR utility

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
st.set_page_config(page_title="DawaKhana", layout="wide", page_icon="static\pills_bottle_logo.svg")

# Custom CSS for Styling
st.markdown("""
    <style>
    .stButton button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 16px;
        transition: background-color 0.3s;
    }
    .stButton button:hover {
        background-color: #45a049;
    }
    .stTextInput input, .stNumberInput input, .stDateInput input {
        border-radius: 5px;
        padding: 10px;
        font-size: 16px;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #2e7d32;
    }
    .stMarkdown p {
        font-size: 16px;
    }
    .stContainer {
        border: 1px solid #e1e4e8;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        background-color: #f9f9f9;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stExpander {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 10px;
    }
    .stToast {
        font-size: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

# Utility: Database Connection
def connect_db():
    return sqlite3.connect('pharmacy.db', check_same_thread=False)

# Utility: Logout Function
def logout():
    st.session_state.clear()
    st.toast("Logged out successfully! 👋", icon="✅")  # Toast message for logout
    st.query_params.clear()  # Clear query parameters
    st.rerun()  # Rerun the app to reflect the logout

# Initialize Cart in Session State
if 'cart' not in st.session_state:
    st.session_state.cart = []

# Login Screen with Sign-Up Option
def login():
    st.title("DawaKhana 💊")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("static/pills_bottle_logo.svg", caption="The ultimate dispensary manager!", width=350)
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
                        st.success(f"Welcome, {st.session_state['username']}! 🎉")
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

    # Remove "Dashboard" from the menu options
    menu_options = ["Manage Drugs", "Add Drug", "Manage Users", "View Orders"]
    selected_option = st.sidebar.radio("Navigate", menu_options)

    if 'username' in st.session_state:
        username = st.session_state['username']
        st.title(f"{username}'s Dashboard")
    st.markdown("---")
    
    # Automatically redirect to "Manage Drugs" if no option is selected
    if selected_option == "Manage Drugs":
        view_drugs()
    elif selected_option == "Add Drug":
        add_drug()
    elif selected_option == "Manage Users":
        manage_users()
    elif selected_option == "View Orders":
        view_orders()

# Display Drugs in a Grid Layout
drug_info = {
    'Paracetamol': '**Primary Use:** Pain reliever and fever reducer.\n\n**Key Benefits:** Effective for mild to moderate pain and fever.\n\n**Important Precautions:** Avoid exceeding recommended dosage to prevent liver damage.',
    'Ibuprofen': '**Primary Use:** Pain reliever and anti-inflammatory.\n\n**Key Benefits:** Reduces pain, inflammation, and fever.\n\n**Important Precautions:** May cause stomach ulcers; use with caution in patients with kidney issues.',
    'Amoxicillin': '**Primary Use:** Antibiotic for bacterial infections.\n\n**Key Benefits:** Treats a wide range of infections.\n\n**Important Precautions:** May cause allergic reactions; complete the full course.',
    'Lisinopril': '**Primary Use:** Treats high blood pressure and heart failure.\n\n**Key Benefits:** Lowers blood pressure and reduces heart failure symptoms.\n\n**Important Precautions:** May cause dizziness; monitor kidney function.',
    'Metformin': '**Primary Use:** Treats type 2 diabetes.\n\n**Key Benefits:** Regulates blood sugar levels.\n\n**Important Precautions:** Use with caution in patients with kidney or liver disease.',
    'Atorvastatin': '**Primary Use:** Treats high cholesterol.\n\n**Key Benefits:** Reduces risk of heart disease.\n\n**Important Precautions:** Monitor liver enzymes regularly.',
    'Omeprazole': '**Primary Use:** Treats acid reflux.\n\n**Key Benefits:** Reduces stomach acid production.\n\n**Important Precautions:** Long-term use may increase risk of bone fractures.',
    'Levothyroxine': '**Primary Use:** Treats hypothyroidism.\n\n**Key Benefits:** Restores thyroid hormone levels.\n\n**Important Precautions:** Monitor thyroid levels regularly.',
    'Amlodipine': '**Primary Use:** Treats high blood pressure.\n\n**Key Benefits:** Lowers blood pressure.\n\n**Important Precautions:** May cause dizziness or swelling.',
    'Simvastatin': '**Primary Use:** Lowers cholesterol.\n\n**Key Benefits:** Reduces risk of heart attack.\n\n**Important Precautions:** Avoid with certain medications.',
    'Losartan': '**Primary Use:** Treats high blood pressure.\n\n**Key Benefits:** Relaxes blood vessels.\n\n**Important Precautions:** Monitor kidney function.',
    'Metoprolol': '**Primary Use:** Treats high blood pressure.\n\n**Key Benefits:** Reduces risk of heart attack.\n\n**Important Precautions:** Use with caution in asthma patients.',
    'Albuterol': '**Primary Use:** Treats asthma.\n\n**Key Benefits:** Relieves bronchospasms.\n\n**Important Precautions:** Use with caution in cardiovascular disease.',
    'Gabapentin': '**Primary Use:** Treats neuropathic pain.\n\n**Key Benefits:** Reduces pain and seizures.\n\n**Important Precautions:** May cause dizziness or drowsiness.',
    'Hydrochlorothiazide': '**Primary Use:** Treats high blood pressure.\n\n**Key Benefits:** Reduces fluid buildup.\n\n**Important Precautions:** Monitor electrolyte levels.',
    'Sertraline': '**Primary Use:** Treats depression.\n\n**Key Benefits:** Improves mood and reduces anxiety.\n\n**Important Precautions:** May cause withdrawal symptoms.',
    'Prednisone': '**Primary Use:** Treats inflammation.\n\n**Key Benefits:** Reduces swelling and pain.\n\n**Important Precautions:** Long-term use may cause side effects.',
    'Tramadol': '**Primary Use:** Treats moderate pain.\n\n**Key Benefits:** Effective pain relief.\n\n**Important Precautions:** May cause dizziness or drowsiness.',
    'Citalopram': '**Primary Use:** Treats depression.\n\n**Key Benefits:** Improves mood.\n\n**Important Precautions:** Monitor for suicidal thoughts.',
    'Warfarin': '**Primary Use:** Prevents blood clots.\n\n**Key Benefits:** Reduces risk of stroke.\n\n**Important Precautions:** Monitor INR regularly.',
    'Methamphetamine': '**Primary Use:** Recreational drug.\n\n**Key Benefits:** None.\n\n**Important Precautions:** Highly addictive and dangerous.',
    'Dolo 650': '**Primary Use:** Treats pain and fever.\n\n**Key Benefits:** Fast relief.\n\n**Important Precautions:** Avoid in liver disease.'
}

def display_drugs_grid(drugs):
    # Responsive grid layout
    cols_per_row = 4
    cols = st.columns(cols_per_row)

    for idx, drug in enumerate(drugs):
        with cols[idx % cols_per_row]:
            # Card container
            with st.container():
                st.image("static\\bottle_blue.svg", caption=drug[1], width=100)
                
                # Dynamic stock status indicator
                stock_level = "high" if drug[2] > 50 else "medium" if drug[2] > 20 else "low"
                stock_color = "green" if stock_level == "high" else "orange" if stock_level == "medium" else "red"
                st.markdown(f"**Stock:** <span style='color: {stock_color}'>{drug[2]} units</span>", unsafe_allow_html=True)
                
                # Price with currency symbol
                st.markdown(f"**Price:** ₹{drug[4]:,.2f}")
                
                # Expiry date with warning if approaching
                expiry_date = datetime.strptime(drug[3], '%Y-%m-%d')
                days_to_expiry = (expiry_date - datetime.now()).days
                expiry_color = "red" if days_to_expiry < 90 else "orange" if days_to_expiry < 180 else "green"
                st.markdown(f"**Expiry:** <span style='color: {expiry_color}'>{drug[3]}</span>", unsafe_allow_html=True)
                
                # Pop-up for detailed information
                with st.popover("More Info"):
                    # Fetch drug description from the drug_info dictionary
                    description = drug_info.get(drug[1], "Description not available.")
                    
                    # Display structured drug details
                    st.markdown(f"### {drug[1]} Details")
                    st.markdown(description)
                
                # Shopping cart functionality for customers
                if st.session_state.get('role') == 'customer':
                    quantity = st.number_input(
                        "Quantity",
                        min_value=1,
                        max_value=drug[2],
                        step=1,
                        key=f"qty_{drug[0]}"
                    )
                    if st.button(
                        "🛒 Add to Cart",
                        key=f"add_{drug[0]}",
                        disabled=drug[2] == 0
                    ):
                        if 'cart' not in st.session_state:
                            st.session_state['cart'] = []
                        
                        # Check if item already in cart
                        cart_item = next(
                            (item for item in st.session_state['cart'] 
                             if item['drug_id'] == drug[0]),
                            None
                        )
                        
                        if cart_item:
                            cart_item['quantity'] += quantity
                            cart_item['total'] = cart_item['quantity'] * cart_item['price']  # Update total
                            st.toast(f"✅ Updated quantity for {drug[1]} in cart!", icon="✅",)  # Toast message
                        else:
                            st.session_state['cart'].append({
                                'drug_id': drug[0],
                                'drug_name': drug[1],
                                'quantity': quantity,
                                'price': drug[4],
                                'expiry': drug[3],
                                'total': quantity * drug[4]  # Add total
                            })
                            st.toast(f"✅ Added {quantity} x {drug[1]} to cart!", icon="✅")  # Toast message
                        
                        # Rerun the app to reflect the updated cart
                        st.rerun()
                st.markdown("---")

# View Cart
def view_cart():
    st.subheader("🛒 Your Cart")
    
    if not st.session_state.cart:
        st.warning("Your cart is empty. Add some drugs to get started!")
        return
    
    # Display cart items in a card-like layout
    total_amount = 0
    for idx, item in enumerate(st.session_state.cart):
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"**{item['drug_name']}**")
                st.caption(f"Price per unit: ₹{item['price']:.2f}")
            
            with col2:
                st.markdown(f"**Quantity:** {item['quantity']}")
                st.markdown(f"**Total:** ₹{item['total']:.2f}")
            
            with col3:
                if st.button(f"❌ Remove", key=f"remove_{idx}"):
                    st.session_state.cart.pop(idx)
                    st.toast(f"Removed {item['drug_name']} from cart!", icon="✅")  # Toast message
                    st.rerun()
            
            st.markdown("---")
            total_amount += item['total']
    
    # Display total amount prominently
    st.markdown(f"### **Total Amount: ₹{total_amount:.2f}**")
    
    # Place Order Button
    if st.button("🚀 Place Order", use_container_width=True):
        place_order_from_cart()

# Place Order from Cart
def place_order_from_cart():
    conn = connect_db()
    c = conn.cursor()
    
    try:
        for item in st.session_state.cart:
            # Check stock availability
            c.execute("SELECT stock FROM medicines WHERE medicine_id = ?", (item['drug_id'],))
            stock = c.fetchone()[0]
            
            if stock < item['quantity']:
                st.error(f"Insufficient stock for {item['drug_name']}. Available: {stock}")
                return
            
            # Insert order into the database
            c.execute("INSERT INTO orders (order_date, customer_id, drug_id, quantity, total_amount) VALUES (?, ?, ?, ?, ?)",
                      (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), st.session_state['user_id'], item['drug_id'], item['quantity'], item['total']))
            
            # Update stock
            c.execute("UPDATE medicines SET stock = stock - ? WHERE medicine_id = ?", (item['quantity'], item['drug_id']))
        
        conn.commit()
        st.toast("Order placed successfully! 🎉", icon="✅")  # Toast message
        st.session_state.cart = []  # Clear the cart immediately
        st.rerun()  # Rerun the app to reflect the empty cart
    except Exception as e:
        st.error(f"Error placing order: {e}")
    finally:
        conn.close()

# View Drugs with Edit and Delete Options
def view_drugs():
    st.subheader("Manage Drugs")
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT * FROM medicines")
    drugs = c.fetchall()
    conn.close()

    # Display drugs in a grid with edit and delete options
    cols_per_row = 4  # Number of columns per row
    cols = st.columns(cols_per_row)  # Create columns for the grid

    for idx, drug in enumerate(drugs):
        with cols[idx % cols_per_row]:
            # Card-like layout for each drug
            with st.container():
                st.image("static\\bottle_blue.svg", caption=drug[1], width=100)  # Drug image
                st.write(f"*Price:* ₹{drug[4]:.2f}")
                st.write(f"*Stock:* {drug[2]}")
                st.write(f"*Expiry:* {drug[3]}")

                # Edit and Delete buttons
                with st.expander("Edit/Delete Drug"):
                    with st.form(key=f"edit_form_{drug[0]}"):
                        new_name = st.text_input("Name", value=drug[1], key=f"name_{drug[0]}")
                        new_stock = st.number_input("Stock", value=drug[2], min_value=0, key=f"stock_{drug[0]}")
                        new_expiry = st.date_input("Expiry Date", value=datetime.strptime(drug[3], '%Y-%m-%d').date(), key=f"expiry_{drug[0]}")
                        new_price = st.number_input("Price (₹)", value=drug[4], min_value=0.0, format="%.2f", key=f"price_{drug[0]}")

                        # Submit button for editing
                        if st.form_submit_button("Save Changes"):
                            conn = connect_db()
                            c = conn.cursor()
                            c.execute("""
                                UPDATE medicines 
                                SET name = ?, stock = ?, expiry_date = ?, price = ?
                                WHERE medicine_id = ?
                            """, (new_name, new_stock, new_expiry.strftime('%Y-%m-%d'), new_price, drug[0]))
                            conn.commit()
                            conn.close()
                            st.toast(f"Updated {new_name} successfully!", icon="✅")
                            st.rerun()

                    # Delete button
                    if st.button(f"Delete {drug[1]}", key=f"delete_{drug[0]}"):
                        conn = connect_db()
                        c = conn.cursor()
                        c.execute("DELETE FROM medicines WHERE medicine_id = ?", (drug[0],))
                        conn.commit()
                        conn.close()
                        st.toast(f"Deleted {drug[1]} successfully!", icon="✅")
                        st.rerun()

                st.markdown("---")

# Add Drug
def add_drug():
    st.subheader("Add New Drug")
    with st.form("add_drug_form"):
        name = st.text_input("Drug Name")
        stock = st.number_input("Stock Quantity", min_value=0, step=1)
        expiry_date = st.date_input("Expiry Date")
        price = st.number_input("Price (₹)", min_value=0.0, format="%.2f")

        if st.form_submit_button("Add Drug"):
            conn = connect_db()
            c = conn.cursor()
            c.execute("INSERT INTO medicines (name, stock, expiry_date, price) VALUES (?, ?, ?, ?)", 
                      (name, stock, expiry_date.strftime('%Y-%m-%d'), price))
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

    # Remove "Search Drugs" from the menu options
    menu_options = ["Buy Drugs", "Order History", "Upload Prescription", "View Cart"]
    selected_option = st.sidebar.radio("Navigate", menu_options)

    if 'username' in st.session_state:
        username = st.session_state['username']
        st.title(f"{username}'s Dashboard")
    st.markdown("---")
    
    if selected_option == "Buy Drugs":
        buy_drugs()
    elif selected_option == "Order History":
        view_order_history()
    elif selected_option == "Upload Prescription":
        upload_prescription()
    elif selected_option == "View Cart":
        view_cart()

# Buy Drugs with Search Functionality
def buy_drugs():
    st.subheader("Available Drugs")
    
    # Add a search bar at the top
    search_query = st.text_input("Search for drugs by name", placeholder="Enter drug names (comma-separated)")
    st.write("\n\n\n")
    conn = connect_db()
    c = conn.cursor()
    
    if search_query:
        # If a search query is provided, filter the drugs
        drug_names = [name.strip() for name in search_query.split(',')]
        query = f"SELECT * FROM medicines WHERE name IN ({','.join(['?'] * len(drug_names))})"
        c.execute(query, drug_names)
        drugs = c.fetchall()
    else:
        # If no search query, display all drugs
        c.execute("SELECT * FROM medicines")
        drugs = c.fetchall()
    
    conn.close()

    # Display the drugs in a grid
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

# Upload Prescription
def upload_prescription():
    st.subheader("Upload Prescription")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        # Display the uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption='Uploaded Prescription', use_container_width=True)
        
        # Extract text from the image
        extracted_text = extract_text_from_image(uploaded_file)
        
        if extracted_text:
            # Display the extracted text in a more structured way
            st.subheader("Extracted Text")
            
            # Use a container to group the extracted text
            with st.container():
                st.markdown("*Full Extracted Text:*")
                st.text_area("Extracted Text", extracted_text, height=200, disabled=True)
            
            # Extract entities using NER
            entities = extract_entities(extracted_text)
            st.subheader("Extracted Entities")
            
            # Use columns to display entities in a grid-like format
            col1, col2 = st.columns(2)
            
            with col1:
                if entities.get("person_name"):
                    st.markdown("*Patient Name:*")
                    st.info(", ".join(entities["person_name"]))
                else:
                    st.markdown("*Patient Name:*")
                    st.warning("No patient name found.")
                
                if entities.get("doctor_name"):
                    st.markdown("*Doctor Name:*")
                    st.info(", ".join(entities["doctor_name"]))
                else:
                    st.markdown("*Doctor Name:*")
                    st.warning("No doctor name found.")
            
            with col2:
                if entities.get("drug_name"):
                    st.markdown("*Drug Name:*")
                    st.info(", ".join(entities["drug_name"]))
                else:
                    st.markdown("*Drug Name:*")
                    st.warning("No drug name found.")
                
                if entities.get("quantity"):
                    st.markdown("*Quantity:*")
                    st.info(", ".join(entities["quantity"]))
                else:
                    st.markdown("*Quantity:*")
                    st.warning("No quantity found.")

            # Check the database for identified drugs
            if entities.get("drug_name"):
                st.subheader("Available Drugs in Database")
                conn = connect_db()
                c = conn.cursor()

                # Query the database for each drug
                available_drugs = []
                for drug in entities["drug_name"]:
                    c.execute("SELECT * FROM medicines WHERE name LIKE ?", (f"%{drug}%",))
                    result = c.fetchone()
                    if result:
                        available_drugs.append(result)

                conn.close()

                if available_drugs:
                    # Display available drugs in a grid
                    st.write("The following drugs are available in the database:")
                    display_drugs_grid(available_drugs)
                else:
                    st.warning("No matching drugs found in the database.")
        else:
            st.error("No text extracted from the image.")

# Main Logic
if 'user_id' not in st.session_state:
    login()
else:
    if st.session_state['role'] == 'admin':
        admin_dashboard()
    else:
        customer_dashboard()