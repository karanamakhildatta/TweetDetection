from flask import Flask,render_template,request,session,redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import uuid
import re
import time
from datetime import date
import pickle
import json
style = "" 
with open('config.json','r') as c:
    params = json.load(c)['params']
app = Flask(__name__)
if (params['local_server']):
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = params['Secret_Key']
db = SQLAlchemy(app)
model = pickle.load(open('model.pkl','rb'))
tfidf = pickle.load(open('vectorizer.pkl','rb'))

class Users(db.Model):
    s_no = db.Column(db.Integer,primary_key=True)    
    first_name = db.Column(db.String(30),nullable=False)    
    last_name = db.Column(db.String(30),nullable=False )    
    mail_id = db.Column(db.String(250),nullable=False )    
    username = db.Column(db.String(8),unique=True,nullable=False )    
    password = db.Column(db.String(16),nullable=False )    
    date_of_birth = db.Column(db.String(120),nullable=False )
    prof_image = db.Column(db.String(120),nullable=True)    
    joined_on = db.Column(db.String(120),nullable=True)

class Tweets(db.Model):  
    tweet_id = db.Column(db.Integer,primary_key=True)
    tweet_text = db.Column(db.String(),nullable=False)
    cyber_bullying = db.Column(db.String(50),nullable=False)
    user_id = db.Column(db.Integer,db.ForeignKey('users.s_no'))
    date_created = db.Column(db.String(120),nullable=True)
class Reports(db.Model):
    report_id = db.Column(db.Integer,primary_key=True)
    report_from = db.Column(db.String(255),db.ForeignKey('users.username'),nullable=False)
    report_text = db.Column(db.String(),nullable=False)
    user_id = db.Column(db.Integer,nullable=False)
    tweet_id = db.Column(db.Integer,db.ForeignKey('tweets.tweet_id'))

@app.route("/login",methods = ['GET', 'POST'])
def login():
    msg = "Sign in to Twitter"
    Type="text-dark"
    name="Welcome to Twitter"
    if(request.method=='POST'):
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = Users.query.filter_by(username=username).first()
            
            if user !=None and user.password == password:
                session['u_name'] = user.username
                return redirect('/')
            else:
                msg = "Invalid Credintials"
                Type = "text-danger"
                name="Login Page"
                return render_template('login.html',msg=msg,color_display=Type,name=name)
        except Exception as e:
            if e:
                msg=f"{e}"


    return render_template('login.html',msg=msg)
@app.route("/",methods = ['GET', 'POST'])
def home():
    if 'u_name' in session:
            style = "font-size:18px;color:rgb(67, 202, 255);"
            name = "Welcome to Twitter"
            message = ""
            Type = ""
            user = Users.query.filter_by(username=session['u_name']).first()

            tweets= db.session.query(Users,Tweets).join(Users).order_by(Tweets.tweet_id.desc()).all()
            if request.method == 'POST':
                if user.username == session['u_name']:
                    tweet_text = request.form.get('tweet-input')
                    tweet_text = re.sub('<[^>]*>','',tweet_text)
                    tweet_text = re.sub(r'[^\w\s]','',tweet_text)
                    tweet_text = tweet_text.lower()
                    data = [tweet_text]
                    vect = tfidf.transform(data).toarray()
                    prediction = model.predict(vect)
                    tweet_text = request.form.get('tweet-input')
                    user_id = user.s_no
                    date_created = date.today()
                    
                    pred = format(prediction[0])
                    if int(pred) == int(1):
                        message = 'Detected as Cyberbullying tweet! If any report is posted your account is peramanetly blocked.'
                        Type = "text_danger"
                        entry = Tweets(tweet_text=tweet_text, user_id = user_id,cyber_bullying=pred,date_created=date_created)
                        db.session.add(entry)
                        db.session.commit()
                        return render_template('index.html',message=message,user=user,style=style,name=name,color_display=Type,tweets = tweets)

                    else:
                        try:
                            entry = Tweets(tweet_text=tweet_text, user_id = user_id,cyber_bullying=pred,date_created=date_created)
                            db.session.add(entry)
                            db.session.commit()

                            return redirect('/')
                        except Exception as e:
                            message = f"{e}"
                            style = "font-size:18px;color:rgb(67, 202, 255);"
                            name = "Welcome to Twitter"
                            return render_template('index.html',message=message,user=user,style=style,color_display=Type,tweets = tweets)
            return render_template('index.html',style=style,user=user,tweets = tweets)

    else:
        
        return redirect('/login')
    
@app.route('/delete/<tweet_id>')
def delete_tweet(tweet_id):
    if 'u_name' in session:
        tweet = Tweets.query.filter_by(tweet_id = tweet_id).first()
        report = Reports.query.filter_by(tweet_id=tweet_id).all()
        user = Users.query.filter_by(username=session['u_name']).first()
        if tweet.user_id == user.s_no:
            if report != None:
                stmt = Reports.__table__.delete().where(Reports.tweet_id == tweet_id)
                db.session.execute(stmt)
                db.session.delete(tweet)
                db.session.commit()
            else:
                db.session.delete(tweet)
                db.session.commit()
            return redirect('/')
        else:
            return redirect('/')
    else:
        return redirect('/')
@app.route("/profile/<user_name>")
def profile(user_name):
    if 'u_name' in session: 
        if user_name == session['u_name']:
            user=Users.query.filter_by(username=session['u_name']).first()
            username = session['u_name']
            style = "font-size:18px;color:rgb(67, 202, 255);"
            name="Profile Page"
            return render_template('profile.html',name=name,user=user,required_user=user,prof_style=style)
        else:
            logged_in_user=Users.query.filter_by(username=session['u_name']).first()
            required_user=Users.query.filter_by(username=user_name).first()
            username = session['u_name']
            if required_user !=None:
                name="Profile Page"
                return render_template('profile.html',name=name,user=logged_in_user,required_user=required_user)
            else:
               return redirect('/')
    else:
        name="Login Page"
        return render_template('login.html',name=name)
@app.route("/register",methods = ['GET', 'POST'])

def register():
    message="Sign Up to Twitter"
    regex = '^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'
    Type = "text-dark"
    flag = 0
    extensions = ['jpg','jpeg','png']
    name="Register to Login"
    if(request.method=='POST'):
        try:
            firstname = request.form.get('firstname')
            lastname = request.form.get('lastname')
            mailid = request.form.get('email')
            username = request.form.get('username')
            password = request.form.get('password')
            dateofbirth = request.form.get('dateofbirth')
            file = request.files['profile']
            joined_on = date.today()
            if firstname !="":
                bool  = firstname.isalpha()
                if(bool ==False): 
                    message="In firstname Special characters or Numbers are not allowed"
                    Type="text-danger"
                    return render_template('register.html',message=message,color_display=Type,name=name)
            if lastname !="":
                bool = lastname.isalpha()
                if(bool == False):
                    Type="text-danger" 
                    message="In Lastname Special characters or Numbers are not allowed"
                    return render_template('register.html',message=message,color_display=Type,name=name)
            if mailid !="":
                user = Users.query.filter_by(mail_id=mailid).first()
                if user != None:
                    message="Email is already taken"
                    Type="text-danger"
                    return render_template('register.html',message=message,color_display=Type,name=name)

                if(re.search(regex,mailid) == None):
                    Type="text-danger"
                    message="Email is improper"
                    
                    return render_template('register.html',message=message,color_display=Type,name=name)
            if username!="":
                if ((len(username)>8) or (len(username)<8)):
                    message="Username must be 8 charcters!"
                    Type="text-danger"
                    return render_template('register.html',message=message,color_display=Type,name=name)
                if not re.search("[0-9]",username):
                    message="Username must contain numbers and charcters!"
                    Type="text-danger"
                    return render_template('register.html',message=message,color_display=Type,name=name)
                if  re.search("[{_^./<>@#%*}()&-+]",username):
                    message="Username must contain numbers and Alphabets!"
                    Type="text-danger"
                    return render_template('register.html',message=message,color_display=Type,name=name)
            if password !="":
                while True:  
                    if (len(password)<8):
                        flag = -1
                        Type="text-danger"
                        message="password is less than 8 charcters."

                        break
                    elif not re.search("[a-z]", password):
                        flag = -1
                        Type="text-danger"
                        message="password must contain small letter."
                        break
                    elif not re.search("[A-Z]", password):
                        flag = -1
                        Type="text-danger"
                        message="password must contain capital letter."
                        break
                    elif not re.search("[0-9]", password):
                        flag = -1
                        Type="text-danger"
                        message="password must contain a number."
                        break
                    elif not re.search("[_@$#%]", password):
                        flag = -1
                        Type="text-danger"
                        message="password must contain a special characters @, $, #, %."
                        break
                    else:
                        flag = 0
                        break
                if flag == -1:
                    Type="text-danger"
                    return render_template('register.html',message=message,color_display=Type,name=name)
                             
            pic_name = secure_filename(file.filename)
            
            if pic_name.split('.')[1] not in extensions:
                Type = "text-danger"
                message="file type must be png, jpg or jpeg"
                return render_template('register.html',message=message,color_display=Type,name=name)
            picture_name = str(uuid.uuid1()) + "."+f"{pic_name.split('.')[1]}"
            file.save(f"static/images/upload/{picture_name}")
            entry = Users(first_name=firstname, last_name = lastname, mail_id = mailid, username= username,password = password,date_of_birth=dateofbirth,joined_on=joined_on,prof_image=picture_name)
            db.session.add(entry)
            db.session.commit()
            Type = "text-success"
            message="Profile Saved Successfully You can Login"
            return render_template('register.html',message=message,color_display=Type,name=name)

            
        except Exception as e:
            m = 0  
            m = str(e).find("Duplicate entry")
            if m>0:
                Type = "text-danger"
                message="Username or Email already Exists"
            else:  
                message=f"{e}"      
                return render_template('register.html',message=message,color_display=Type,name=name)
          
                

    return render_template('register.html',message=message,color_display=Type,name=name)

@app.route("/logout")
def logout():
    session.pop('u_name')
    return redirect('/')
@app.route("/update/<user_name>",methods = ['GET', 'POST'])
def edit(user_name):
    message="Update Your Account"
    Type='text-info'
    name="Update "+user_name
    if 'u_name' in session:
        if user_name == session['u_name']:
            regex = '^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'
            user = Users.query.filter_by(username=session['u_name']).first()
            if(request.method=='POST'):
                
                firstname = request.form.get('firstname')
                lastname = request.form.get('lastname')
                mailid = request.form.get('email')
                username = request.form.get('username')
                dateofbirth = request.form.get('dateofbirth')
                if firstname !=user.first_name:
                    bool  = firstname.isalpha()
                    if(bool ==False): 
                        message="In firstname Special characters or Numbers are not allowed"
                        Type="text-danger"
                        return render_template('edit.html',message=message,color_display=Type,name=name,user=user)
                if lastname !=user.last_name:
                    bool = lastname.isalpha()
                    if(bool == False):
                        Type="text-danger" 
                        message="In Lastname Special characters or Numbers are not allowed"
                        return render_template('edit.html',message=message,color_display=Type,name=name,user=user)
                if mailid != user.mail_id:
                    ruser = Users.query.filter_by(mail_id=mailid).first()
                    if ruser != None:
                        message="Email is already taken!"
                        Type="text-danger"
                        return render_template('edit.html',message=message,color_display=Type,name=name,user=user)

                    if(re.search(regex,mailid) == None):
                        Type="text-danger"
                        message="Email is improper"
                        
                        return render_template('edit.html',message=message,color_display=Type,name=name,user=user)
                ruser =  Users.query.filter_by(username=username).first()
                if username!=user.username:
                    if ((len(username)>8) or (len(username)<8)):
                        message="Username must be 8 charcters!"
                        Type="text-danger"
                        return render_template('edit.html',message=message,color_display=Type,name=name,user=user)
                    if ruser != None:
                        message="Username already taken!"
                        Type="text-danger"
                        return render_template('edit.html',message=message,color_display=Type,name=name,user=user)
                    if not re.search("[0-9]",username):
                        message="Username must contain numbers and charcters!"
                        Type="text-danger"
                    return render_template('edit.html',message=message,color_display=Type,name=name)
                    if  re.search("[{_^./<>@#%*}()&-+]",username):
                        message="Username must contain numbers and Alphabets!"
                        Type="text-danger"
                        return render_template('edit.html',message=message,color_display=Type,name=name)
                
                user.first_name = firstname
                user.last_name  = lastname
                user.mail_id    = mailid
                user.username   = username
                user.date_of_birth = dateofbirth
                
                try:
                    db.session.commit()
                    if username != session['u_name']:
                        session.pop('u_name')
                        session['u_name'] = username
                        return redirect(f"/profile/{session['u_name']}")
                    else:
                        return redirect(f"/profile/{user.username}")
                except Exception as e:
                    message = "Failed to update check your db connection."
                    Type = 'text-danger'
            return render_template('edit.html',message=message,color_display=Type,user=user)
        else:
            return redirect('/')
    else:
        return redirect('/')
@app.route('/profile/password/update/<user_name>',methods = ['GET', 'POST'])
def update_password(user_name):
    message = "Update Your Password"
    Type = 'text-info'
    user = Users.query.filter_by(username=user_name).first()
    if 'u_name' in session:
        if user_name == session['u_name']:
                if request.method ==  'POST':
                    current_password = request.form.get('current_password')
                    new_password = request.form.get('new_password')
                    confirm_password = request.form.get('confirm_password')
                    user =  Users.query.filter_by(username=session['u_name']).first()
                    if user.password ==  current_password:
                        if new_password == confirm_password:
                            while True:  
                                if (len(new_password)<8):
                                    flag = -1
                                    Type="text-danger"
                                    message="password is less than 8 charcters."
                                    break
                                elif not re.search("[a-z]", new_password):
                                    flag = -1
                                    Type="text-danger"
                                    message="password must contain small letter."
                                    break
                                elif not re.search("[A-Z]", new_password):
                                    flag = -1
                                    Type="text-danger"
                                    message="password must contain capital letter."
                                    break
                                elif not re.search("[0-9]", new_password):
                                    flag = -1
                                    Type="text-danger"
                                    message="password must contain a number."
                                    break
                                elif not re.search("[_@$#%]", new_password):
                                    flag = -1
                                    Type="text-danger"
                                    message="password must contain a special characters @, $, #, %."
                                    break
                                else:
                                    flag = 0
                                    break
                            if flag == -1:
                                Type="text-danger"
                                return render_template('update_password.html',message=message,color_display=Type,user=user)
                            else:
                                user.password = new_password
                                db.session.commit()
                                message = "Password Updated Successfully."
                                Type = "text-success"
                                return render_template('update_password.html',message=message,color_display=Type,user=user)
        else:
            return redirect('/')
    else:
        return redirect('/')


    
    return render_template('update_password.html',message=message,color_display=Type,user=user)
@app.route('/profile/picture/update/<user_name>',methods=['GET','POST'])
def update_profile_picture(user_name):
    if 'u_name' in session:
        if user_name == session['u_name']:
            user = Users.query.filter_by(username=session['u_name']).first()
            print(user.first_name)
            message = 'Update Your Profile Picture'
            Type = "text-info"
            extensions = ['jpg','jpeg','png']
            if request.method == 'POST':
                file = request.files['profile']
                pic_name = secure_filename(file.filename)
                if pic_name.split('.')[1] not in extensions:
                    Type = "text-danger"
                    message="file type must be png, jpg or jpeg"
                    return render_template('update_profile_picture.html',message=message,color_display=Type,user=user)
                picture_name = user.prof_image
                file.save(f"static/images/upload/{picture_name}")
                return redirect('/profile')

            return render_template('update_profile_picture.html',user=user,message=message,color_display=Type)
        else:
            return redirect('/')
    else:
        return redirect('/')


@app.route('/tweet/report/<tweet_id>',methods=['GET','POST'])
def report_tweet(tweet_id):
    if 'u_name' in session:
        user = Users.query.filter_by(username=session['u_name']).first()
        tweet= db.session.query(Tweets,Users).filter_by(tweet_id=tweet_id).join(Users).first()
        if tweet != None:
            if tweet[1].username == user.username:
                return redirect('/')
            else:
                if request.method == 'POST':
                    report_text = request.form.get('report_text')
                    report_from = user.s_no
                    user_id = tweet[1].s_no
                    tweet_id = tweet[0].tweet_id
                    report = Reports(report_text=report_text,report_from=report_from,user_id=user_id,tweet_id=tweet_id)
                    db.session.add(report)
                    db.session.commit()
                    message = "Report Successfully Registered "
                    Type = "text_success"
                    return render_template('report_tweet.html',message=message,color_display=Type,user=user,tweet=tweet)
                return render_template('report_tweet.html',user=user,tweet=tweet)
        else:
            return redirect('/')
    else:
        return redirect('/')
@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        admin_email = request.form.get('admin_email')
        admin_password = request.form.get('admin_password')
        if (admin_email == params['admin_email'] and admin_password == params['admin_password']):
            session['a_name'] = params['admin_name']
            return redirect('/admin/users')
    return render_template('admin_login.html')
@app.route('/admin/users')
def fetch_users():
    if 'a_name' in session:
        users = Users.query.all()
        admin = session['a_name']
        return render_template('all_users.html',users=users,admin=admin)
    else:
        return redirect('/admin/login')
@app.route('/admin/tweets')
def fetch_tweets():
    if 'a_name' in session:
        tweets= db.session.query(Tweets,Users).join(Users).all()
        admin = session['a_name']
        return render_template('all_tweets.html',tweets=tweets,admin=admin)
    else:
        return redirect('/admin/login')

@app.route('/admin/reports')
def fetch_reports():
    if 'a_name' in session:
        results = db.session.query(Reports,Users,Tweets).select_from(Reports).join(Tweets).join(Users).all()
        admin = session['a_name']
        Report_list = []
        for result in results:
            result = list(result)
            m = Users.query.filter_by(s_no=result[0].report_from).first()
            result.append(m)
            Report_list.append((result))
        return render_template('all_reports.html',reports=Report_list,admin=admin)
    else:
        return redirect('/admin/login')
@app.route('/admin/logout')
def admin_logout():
    if 'a_name' in session:
        session.pop('a_name')
        return redirect('/admin/login')
@app.route('/admin/users/<user_id>')
def delete_user(user_id):    
    if 'a_name' in session:
        user = Users.query.filter_by(s_no = user_id).first()
        if user !=None:
            stmt = Tweets.__table__.delete().where(Tweets.user_id == user_id)
            stmt1 = Reports.__table__.delete().where(Reports.user_id == user_id)
            db.session.execute(stmt1)
            db.session.execute(stmt)
            db.session.delete(user)
            db.session.commit()
            return redirect('/admin/users')
        else:
            return redirect('/admin/users')
    else:
        return redirect('/admin/login')
@app.route('/admin/tweet/<tweet_id>')
def delete_tweets(tweet_id):    
    if 'a_name' in session:
        tweet = Tweets.query.filter_by(tweet_id = tweet_id).first()
        if tweet !=None:
            stmt = Reports.__table__.delete().where(Reports.tweet_id == tweet_id)
            db.session.execute(stmt)
            db.session.delete(tweet)
            db.session.commit()
            return redirect('/admin/tweets')
        else:
            return redirect('/admin/tweets')
    else:
        return redirect('/admin/login')

@app.route('/admin/report/<report_id>')
def delete_reports(report_id):    
    if 'a_name' in session:
        report = Reports.query.filter_by(report_id = report_id).first()
        if report !=None:
            db.session.delete(report)
            db.session.commit()
            return redirect('/admin/reports')
        else:
            return redirect('/admin/reports')
    else:
        return redirect('/admin/login')

if __name__ == "__main__":
    app.run(debug=True)