from flask import Flask, render_template, redirect, url_for, flash, request, current_app
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, Recipe, Comment
from forms import RegistrationForm, LoginForm, RecipeForm, CommentForm
from werkzeug.utils import secure_filename
import os


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config.from_object(Config)

app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static/uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#   -------   Register Form  -----------------
@app.route('/register', methods = ['GET', 'POST'])
def register():
    form= RegistrationForm()
    if request.method == 'POST':
        username = request.form['name']
        email = request.form['email']
        password = request.form['password']
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("User already existed with this email!", "danger")
            return redirect(url_for('register'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# -------------   Login Form ---------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check email and password.', 'danger')
    return render_template('login.html', form=form)

# ------- Dashboard -----------
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


# -----------   Logout --------------
@app.route('/logout')
@login_required
def logout():
    logout_user()  
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))





# -----------   home  --------------
@app.route('/')
def home():
    search_query = request.args.get('search', '')
    if search_query:
        recipes = Recipe.query.filter(Recipe.title.ilike(f'%{search_query}%')).all()
    else:
        recipes = Recipe.query.all()
    return render_template('home.html', recipes=recipes)





# -----------   recipe create  --------------
@app.route('/post', methods=['GET', 'POST'])
@login_required
def post_recipe():
    form = RecipeForm()
    if form.validate_on_submit():
        image_file = None
        if form.image.data:
            file = form.image.data
            if allowed_file(file.filename):
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filename = secure_filename(file.filename)
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                image_file = filename
            else:
                flash('Invalid image format. Allowed: png, jpg, jpeg, gif', 'danger')
                return render_template('post.html', form=form)

        recipe = Recipe(title=form.title.data, ingredients=form.ingredients.data, steps=form.steps.data, image=image_file, author=current_user)
        db.session.add(recipe)
        db.session.commit()
        flash('Recipe posted successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('post.html', form=form)


# ---------- Recipe  ---  Update /  Edit ---------------------

@app.route('/recipe/<int:recipe_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.author != current_user:
        flash('You are not allowed to edit this recipe.', 'danger')
        return redirect(url_for('home'))
    form = RecipeForm(obj=recipe)  
    if form.validate_on_submit():
        recipe.title = form.title.data
        recipe.ingredients = form.ingredients.data
        recipe.steps = form.steps.data

        if form.image.data:
            file = form.image.data
            if allowed_file(file.filename):
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filename = secure_filename(file.filename)
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                recipe.image = filename

        db.session.commit()
        flash('Recipe updated successfully!', 'success')
        return redirect(url_for('recipe_detail', recipe_id=recipe.id))

    return render_template('edit_recipe.html', form=form, recipe=recipe)


#  -------------   Delete ----------------
@app.route('/recipe/delete/<int:recipe_id>', methods=['POST'])
@login_required
def delete_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)

    if recipe.author != current_user:
        flash("You don't have permission to delete this recipe.", "danger")
        return redirect(url_for('home'))
    
    if recipe.image:
        image_path = os.path.join(current_app.root_path, 'static/uploads', recipe.image)
        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.delete(recipe)
    db.session.commit()
    flash("Recipe deleted successfully!", "success")
    return redirect(url_for('home'))


# -----------   details  --------------
@app.route('/recipe/<int:recipe_id>', methods=['GET', 'POST'])
def recipe_detail(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, author=current_user, recipe=recipe)
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
        return redirect(url_for('recipe_detail', recipe_id=recipe.id))
    
    comment = Comment.query.filter_by(recipe_id=recipe.id).order_by(Comment.timestamp.desc()).all()
    return render_template('detail.html', recipe=recipe, form=form, comment=comment)


# -----------  Like Recipe ---------------------
@app.route('/recipe/<int:recipe_id>/like', methods=['POST'])
@login_required
def like_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if current_user in recipe.liked_by:
        recipe.liked_by.remove(current_user)
    else:
        recipe.liked_by.append(current_user)
    db.session.commit()
    return redirect(request.referrer)


if __name__ == '__main__':
    app.run(debug=True)


