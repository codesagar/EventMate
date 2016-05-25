import fuzzywuzzy
from fuzzywuzzy import fuzz
from azure.storage.blob import BlockBlobService
from fuzzywuzzy import process
import unirest
from flask import Flask, redirect, url_for, render_template, session, flash, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, UserMixin, login_user, logout_user,\
    current_user
from oauth import OAuthSignIn
from flask.ext.wtf import Form
from wtforms import StringField, SubmitField, IntegerField
from wtforms.validators import Required, Length, NumberRange, Optional, Email
from flask.ext.bootstrap import Bootstrap
import requests
from werkzeug import secure_filename
import os

UPLOAD_FOLDER = '/home/'
app = Flask(__name__)
app.config['SECRET_KEY'] = 'top secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OAUTH_CREDENTIALS'] = {
    'facebook': {
        'id': '589799337851828',
        'secret': '817c867793bf4d5d1b9d66f3d7ee8da7'
    },
    'twitter': {
        'id': 'nizrwHKP6SRGKlDjPT6UNj8LE',
        'secret': 'FsMAqtq2YlurPdfD8NHTn0ZDq2nybnzVqzY5gdV1QB6LqJONen'
    }
}
app.config.from_pyfile('config.py')
account = app.config['ACCOUNT']   # Azure account name
key = app.config['STORAGE_KEY']      # Azure Storage account access key  
container = app.config['CONTAINER'] # Container name

bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
lm = LoginManager(app)
lm.login_view = 'index'
blob_service = BlockBlobService(account_name=account, account_key=key)
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    nickname = db.Column(db.String(64), nullable=True)
    email = db.Column(db.String(64), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    date = db.Column(db.String(10),nullable=True)
    pro_pic = db.Column(db.String(128), nullable=True)
    country = db.Column(db.String(32), nullable=True)
    skills = db.Column(db.String(40),nullable=True)
    about = db.Column(db.String(400),nullable=True)
    
class Question(db.Model):
    __tablename__='questions'
    id = db.Column(db.Integer,primary_key=True)
    content = db.Column(db.String(250))
    relevance = db.Column(db.Boolean,default=1)
    frequency = db.Column(db.Integer,default=1)
    creator_id = db.Column(db.Integer,nullable=True)
    event_id = db.Column(db.Integer,nullable=True)
    
class NameForm(Form):
    name = StringField('Username:', validators=[Required('The UserName field is empty') ,Length(3,130,'UserName should contain between 3 to 130 characters.')])
    age = IntegerField('Age:', validators=[Required('The age Field is required.') ,NumberRange(12,130,'Age should be between 12 and 130.')])
    email = StringField('Email:',validators=[Optional(),Email('Please Enter a proper Email Address')])
    submit = SubmitField('Submit')


class Event(db.Model):
    __tablename__='events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64),nullable=True)
    category = db.Column(db.String(64),nullable=True)
    start_date = db.Column(db.String(10),nullable=True)
    end_date = db.Column(db.String(10),nullable=True)
    event_type = db.Column(db.String(5),nullable=True)
    venue = db.Column(db.String(100),nullable=True)
    creator_id = db.Column(db.Integer, nullable = False)
    img = db.Column(db.String(100),nullable=True)
    
    
# class fl(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     links = db.Column(db.String(64),nullable=True)

class QuestionForm(Form):
    question = StringField('Question:',validators=[Required('Do not leave empty')])
    submit = SubmitField('Submit')

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if not current_user.is_anonymous:
        user = User.query.filter_by(social_id=current_user.social_id).first()
        if not user.age:
            if form.validate_on_submit():
                user.age = form.age.data
                user.nickname = form.name.data
                if form.email.data:
                    user.email = form.email.data
                db.session.add(user)
                db.session.commit()      
    return render_template('index.html', form=form)

@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@app.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    social_id, username, email = oauth.callback()
    if social_id is None:
        flash('Authentication failed.')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()
    if not user:
        user = User(social_id=social_id,nickname=email,email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user, True)
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    return render_template('viewpro.html')

@app.route('/fileserver',methods=['GET', 'POST'])
def file():
    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)
        # fileextension = filename.rsplit('.',1)[1]
        # Randomfilename = 'sagar'
        # filename = Randomfilename + '.' + fileextension
        try:
            blob_service.create_blob_from_stream(container, filename, file)
        except Exception:
            print 'Exception=' , Exception 
            pass
        ref =  'http://'+ account + '.blob.core.windows.net/' + container + '/' + filename
        print ref
    return render_template('file.html')

@app.route('/editprofile',methods=['GET', 'POST'])
def editprofile():
    if request.method == 'POST':
        if current_user.is_anonymous:
            return redirect(url_for('index'))
        user = User.query.filter_by(social_id=current_user.social_id).first()
        if not user:
            return redirect(url_for('index'))
        user.nickname=request.form['Name']
        user.email=request.form['Email']
        user.date=request.form['DOB']
        user.country=request.form['Country']
        user.sex="Male"
        user.about=request.form['About']
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('profile'))

       
    return render_template('editpro.html')

@app.route('/eventcreation', methods=['GET', 'POST'])
def eventcreation():
    if current_user.is_anonymous:
            return redirect(url_for('index'))
    if request.method == 'POST':
        event = Event(title = request.form['Title'],start_date=request.form['StartDate'],end_date=request.form['EndDate'],venue=request.form['EveVenue'],category = request.form['Category'],event_type=request.form['Type'])
        event.creator_id = current_user.social_id
        file = request.files['file']
        filename = secure_filename(file.filename)
        fileextension = filename.rsplit('.',1)[1]
        filename = current_user.nickname + '.' + fileextension
        # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        try:
            blob_service.create_blob_from_stream(container, filename, file)
        except Exception:
            print 'Exception=' , Exception 
            pass
        ref =  'http://'+ account + '.blob.core.windows.net/' + container + '/' + filename
        print ref
        event.img = ref
        db.session.add(event)
        db.session.commit()
    return render_template('eventcreation.html')

@app.route('/bang', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)
        fileextension = filename.rsplit('.',1)[1]
        filename = current_user.nickname + '.' + fileextension
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return '''
        <!doctype html>
        <title>File Link</title>
        <h1>Uploaded File Link</h1>
        '''
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''



#--view events
@app.route('/viewevent/<eventid>', methods=['GET', 'POST'])
def viewevent(eventid):
    if current_user.is_anonymous:
        return redirect(url_for('index'))
    event = Event.query.filter_by(id=eventid).first()
    if request.method == 'POST':
        print('This is running')
        ques = request.form['ques']
        new_ques = Question(content = ques,creator_id = current_user.social_id,event_id = eventid)
        for sample in Question.query.filter_by(relevance = 1).filter_by(event_id = eventid):
            response = unirest.post("https://amtera.p.mashape.com/relatedness/en",headers={"X-Mashape-Key": "u4kxLBXvcomshaXdgapkkrdfh3EFp15R7FojsnLlMr1IAO9wqA","Content-Type": "application/json","Accept": "application/json"},params=("{\"t1\":\""+sample.content+"\",\"t2\":\""+new_ques.content+"\"}"))
            responseF = fuzz.ratio(sample.content,new_ques.content)
            if response.body['v'] > 0.7 or responseF > 70:
                new_ques.relevance = 0
                new_freq = sample.frequency + 1
                sample.frequency = new_freq
                db.session.add(sample)      
        db.session.add(new_ques)
        db.session.commit()
    
    return render_template('viewevent.html',event=event,Question=Question.query.filter_by(relevance=1).filter_by(event_id=eventid).order_by(Question.frequency.desc()).all())

@app.route('/listevents',methods=['GET', 'POST'])
def listevents():
    if current_user.is_anonymous:
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=current_user.social_id).first()
    return render_template('listevents.html',Event=Event.query.all())



if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
