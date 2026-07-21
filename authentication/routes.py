import re
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from database_models.models import db, User, ActivityLog

auth = Blueprint('auth', __name__)

def is_valid_email(email):
    """
    Simple email validation check.
    """
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def is_strong_password(password):
    """
    Validates password strength:
    - Min 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    if not any(c in "!@#$%^&*()-_=+[]{}|;:',.<>?/`~" for c in password):
        return False, "Password must contain at least one special character."
    return True, "Strong password."

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('dashboard'))
        return redirect(url_for('candidate_portal'))
        
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'candidate') # 'candidate' or 'admin'
        
        # Validations
        if not full_name or not username or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template('register.html')
            
        if not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
            return render_template('register.html')
            
        is_strong, pw_msg = is_strong_password(password)
        if not is_strong:
            flash(pw_msg, "danger")
            return render_template('register.html')
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html')
            
        # Duplicate checks
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("Username or Email already registered.", "danger")
            return render_template('register.html')
            
        try:
            # Create user
            new_user = User(
                username=username,
                email=email,
                full_name=full_name,
                role=role,
                theme_preference='corporate-blue' # Default theme
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            # Log action
            ip = request.remote_addr
            log = ActivityLog(user_id=new_user.id, action="Registered new account", ip_address=ip)
            db.session.add(log)
            db.session.commit()
            
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred during registration: {e}", "danger")
            
    return render_template('register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('dashboard'))
        return redirect(url_for('candidate_portal'))
        
    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip() # Can be username or email
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False
        
        if not login_id or not password:
            flash("Please enter both credentials.", "danger")
            return render_template('login.html')
            
        # Support email or username login
        user = User.query.filter((User.email == login_id) | (User.username == login_id)).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            
            # Log action
            ip = request.remote_addr
            log = ActivityLog(user_id=user.id, action="Logged in", ip_address=ip)
            db.session.add(log)
            db.session.commit()
            
            flash(f"Welcome back, {user.full_name}!", "success")
            if user.role == 'admin':
                return redirect(url_for('dashboard'))
            return redirect(url_for('candidate_portal'))
        else:
            flash("Invalid credentials. Please try again.", "danger")
            
    return render_template('login.html')


@auth.route('/logout')
@login_required
def logout():
    # Log action
    user_id = current_user.id
    ip = request.remote_addr
    log = ActivityLog(user_id=user_id, action="Logged out", ip_address=ip)
    db.session.add(log)
    db.session.commit()
    
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for('auth.login'))


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()
        if user:
            # Here we would send a reset email. For this simulation, we reset to a temp password
            temp_pw = "ResetPass123!"
            user.set_password(temp_pw)
            db.session.commit()
            flash(f"Password reset request received. For simulation, your password is reset to: {temp_pw}", "info")
            return redirect(url_for('auth.login'))
        else:
            flash("Email address not found.", "danger")
    return render_template('login.html', forgot=True)
