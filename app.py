from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import User, Task, Tag
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'teamtasksecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uid = request.form['uid']
        pwd = generate_password_hash(request.form['pwd'])
        if User.query.count() == 0:
            role = 'admin'
        else:
            role = 'user'

        if User.query.filter_by(uid=uid).first():
            flash('User ID already exists!', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(uid=uid, pwd=pwd, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash('Registered successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uid = request.form['uid']
        pwd = request.form['pwd']
        user = User.query.filter_by(uid=uid).first()

        if user and check_password_hash(user.pwd, pwd):
            login_user(user)
            if user.role in ['admin', 'mod']:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
            
        flash('Invalid credentials', 'danger')
    return render_template('login.html')
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    all_meetups = Task.query.all()
    return render_template('dashboard.html', tasks=all_meetups)

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role not in ['admin', 'mod']:
        flash("Access denied", 'danger')
        return redirect(url_for('dashboard'))
    
    tasks = Task.query.all()
    suggested_tags = Tag.query.filter_by(status='suggested').all()
    return render_template('admin_dashboard.html', tasks=tasks, suggested_tags=suggested_tags)

@app.route('/admin/approve_tag/<int:tag_id>')
@login_required
def approve_tag(tag_id):
    if current_user.role not in ['admin', 'mod']:
        return redirect(url_for('dashboard'))
    
    tag = Tag.query.get_or_404(tag_id)
    tag.status = 'approved'
    db.session.commit()
    flash(f'Tag "{tag.name}" approved!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        location = request.form['location']
        max_attendees = int(request.form['max_attendees'])
        tag_id = int(request.form['tag_id'])
        
        start_time_str = request.form['startTime']
        start_time_obj = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        
        shared_with_id = request.form.get('shared_with')
        shared_with_id = int(shared_with_id) if shared_with_id else None

        new_task = Task(
            title=title, 
            description=description, 
            location=location,
            created_by=current_user.id, 
            shared_with=shared_with_id,
            startTime=start_time_obj,
            max_attendees=max_attendees,
            tag_id=tag_id
        )

        db.session.add(new_task)
        db.session.commit()
        flash('Meetup created!', 'success')
        return redirect(url_for('dashboard'))

    approved_tags = Tag.query.filter_by(status='approved').all()
    return render_template('add_task.html', tags=approved_tags)

@app.route('/suggest_tag', methods=['POST'])
@login_required
def suggest_tag():
    tag_name = request.form['tag_name']
    if Tag.query.filter_by(name=tag_name).first():
        flash('Tag already exists or is pending approval.', 'warning')
    else:
        db.session.add(Tag(name=tag_name, status='suggested'))
        db.session.commit()
        flash('Tag suggested and awaiting admin approval!', 'success')
    return redirect(url_for('add_task'))

@app.route('/rsvp/<int:task_id>', methods=['POST'])
@login_required
def rsvp(task_id):
    task = Task.query.get_or_404(task_id)
    
    if not task.isActive:
        flash("This meetup is full or no longer active.", "danger")
        return redirect(url_for('dashboard'))
        
    if current_user.id == task.created_by:
        flash("You are the host of this meetup.", "info")
        return redirect(url_for('dashboard'))

    task.current_attendees += 1
    db.session.commit()
    
    flash("Successfully joined the meetup!", "success")
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if current_user.id != task.created_by and current_user.role not in ['admin', 'mod']:
        flash("Access denied", "danger")
        return redirect(url_for('dashboard'))
    
    db.session.delete(task)
    db.session.commit()
    flash('Meetup deleted', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Tag.query.first():
            defaults = ['Wander', 'Movie?', 'Study Sesh', 'Grab Lunch', 'Games?', 'Party']
            for t in defaults:
                db.session.add(Tag(name=t, status='approved'))
            db.session.commit()
    app.run(debug=True)