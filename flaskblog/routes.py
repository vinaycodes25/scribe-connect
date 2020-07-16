import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort,request
from flaskblog import app, db, bcrypt ,mail
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm
from flaskblog.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Mail, Message

import socket      #this for email if not attached this it will give error

socket.getaddrinfo('localhost',5000)




@app.route("/home")
@login_required
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('home.html', posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', title='About')

@app.route("/")
@app.route("/register", methods=['GET', 'POST'])
def register():
    scribe_or_blind=''
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        if request.form.get('blind'):
            scribe_or_blind='blind'
        else:
            scribe_or_blind='scribe'

        user = User(username=form.username.data, email=form.email.data, password=hashed_password,status=scribe_or_blind)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout",methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(exam_date=form.exam_date.data, phone_number=form.phone_number.data , address=form.address.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Request',
                           form=form, legend='Create a Request for Scribe(fill this only if you are blind) ')


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.exam_date = form.exam_date.data
        post.phone_number = form.phone_number.data
        post.address = form.address.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.exam_date.data = post.exam_date
        form.address.data = post.address
    return render_template('create_post.html', title='Update Request',
                           form=form, legend='Update Request')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)
    

@app.route("/accept_request/<string:user_email>/<string:student_email>",methods=['GET', 'POST'])
def accept_request(user_email,student_email):
    email_list_user=[]
    email_list_user=list(email_list_user)
    user = User.query.filter_by(email = user_email).all()
    for i in user:
        email_list_user.append(i.email)
    
    msg = Message('Scribe Finder', sender = 'vinayvins2000@gmail.com', recipients = email_list_user)
    msg.body = "Scribe Request to "+user[0].username
    mail.send(msg)
    flash('email sent', 'success')

    
    email_list_student=[]
    email_list_student=list(email_list_student)
    student = User.query.filter_by(email=student_email).all()
    for i in student:
        email_list_student.append(i.email)
    
    student_body = "Dear student "+student[0].username+" has accepted your scribe request"
    student_msg = Message('Scribe Connect', sender = 'vinayvins2000@gmail.com', recipients = email_list_student)
    student_msg.body = student_body
    mail.send(student_msg)
    print(student[0].username,user[0].username)
    

    return redirect(url_for('home'))




