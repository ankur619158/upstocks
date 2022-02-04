from flask import Flask,render_template,session,redirect,request
from flask_session import Session
import sqlite3 as sql
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timezone
from flask_mail import Mail,Message
import requests
import json
import urllib.parse
import datetime

con = sql.connect(r'C:\Users\Home\sqlite\upstocks.db' , check_same_thread=False)
cur = con.cursor()

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

mail=Mail(app)

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'ankurshukla146@gmail.com'
app.config['MAIL_PASSWORD'] = 'Aristarchus@123'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)


@app.route("/" , methods = ["GET" , "POST"])
def index():
    if session.get("userid") is None:
        return redirect("/login")
    name = str(session.get("userid"))
    datas = cur.execute("SELECT symbol,shares,price,date FROM folio where username = ?;" , (name ,)).fetchall()
    price = cur.execute("SELECT cash FROM users where username = ?;",(name ,))
    
    return render_template("upstocks.html",datas=datas)


@app.route("/login" , methods = ["GET","POST"])
def login():
    if request.method == "POST":
        name = request.form["username"]
        print(name)
        password = request.form["password"]
        print(password)
        rows = cur.execute("SELECT * FROM users WHERE username = ?;",(name,))
        if rows == "None":
            return render_template("error.html" , message = "incorrect credentials")
        data = []
        for row in rows:
            data.append(row)
        print(data)
        if len(data) == 0:
            return render_template("error.html" , message = "invalid credentials")
        else:
            if check_password_hash(data[0][2] , password):
                session['userid'] = name
                return redirect("/")
            else:
                
                return render_template("error.html",message = "invalid password")
    else:
        return render_template("login.html" , message = "enter username and password")

@app.route("/signup" , methods = ["GET","POST"])
def signup():
    if request.method == "POST":
        name = request.form['username']
        print(name)
        password = request.form['password']
        print(password)
        c_password = request.form['cpassword']
        print(c_password)
        if password == c_password:
            print("done")
            cur.execute("INSERT INTO users (username,hash) VALUES (?,?);",(name,generate_password_hash(password)))
            session['userid'] = name
            con.commit()
            return redirect("/")
        else:
            return render_template("error.html" , message = "both password didn't match")
    else:
        return render_template("signup.html")

@app.route("/buy" , methods = ["GET","POST"])
def buy():
    if session.get("userid") is None:
        return redirect("/")
    if request.method == "POST":
        symbol = request.form['symbol']
        symbol = symbol.upper()
        shares = request.form['shares']
        symbol = symbol.upper()
        look = lookup(symbol)
        if not look:
            return render_template("error.html" , message = "API PROCESS IS NOT WORKING")
        username = str(session.get("userid"))
        line = cur.execute("select * from users where username = ?",(username,))
        line = list(line)
        cash = line[0][3]
        value = int(look["price"])*int(shares)
        if value < cash:
            cur.execute("UPDATE users SET cash = cash - ? WHERE username = ?",(int(value), username))
            con.commit()
            # Add the transaction to the user's history
            cur.execute("INSERT INTO history (username, operation, symbol, price, shares) VALUES (?,?,?,?,?)",(username,'BOUGHT',look['symbol'],look['price'],shares))
            con.commit()
            # Add the stock to the user's portfolio
            row = cur.execute("SELECT * FROM folio where symbol = ? and username = ?;",(symbol,username)).fetchall()
            if row:
                cur.execute("UPDATE folio SET shares = shares + ? where symbol = ? and username = ? ;",(shares,symbol,username))
                con.commit()
            else:
                date= datetime.datetime.now()
                cur.execute("INSERT INTO folio (username, symbol, shares,price,date) VALUES (?,?,?,?,?)",(username,look['symbol'],shares,int(value),date))
                con.commit()
        else:
            return render_template("error.html",message = "you donot have enough money")
        return render_template("upstocks.html", bmessage = "Bought")
        
    else:
        return render_template("upstocks.html")

@app.route("/sell" , methods = ["GET","POST"])
def sell():
    username = str(session.get("userid") )
    if request.method == "POST":
        symbol = request.form['symbol']
        symbol = symbol.upper()
        shares = int(request.form['shares'])
        symbols = cur.execute("SELECT symbol FROM folio WHERE username = ?;",(username,)).fetchall()
           
        sym = []
        for i in symbols:
            sym.append(i[0])
        print(sym)
        
        if symbol not in sym:
            return render_template("error.html",message = "you don't have this company shares")
        look = lookup(symbol)
        
        if not look:
            return render_template("error.html" , message = "API PROCESS IS NOT WORKING")

        value = int(look["price"])*int(shares)
        
        shares_v = cur.execute("SELECT shares FROM folio WHERE username = ? and symbol = ?;",(username,symbol)).fetchone()
        
        
        if (int(shares_v[0]) < shares):
            return render_template("error.html" , message = "not enough shares")
        else:
            cur.execute("UPDATE users SET cash = cash + ? where username = ?",(int(value) , username))
            con.commit()
            cur.execute("INSERT INTO history (username,operation,symbol,price,shares) VALUES (?,?,?,?,?)",(username,'SOLD',look['symbol'],look['price'] , shares))
            con.commit()
            
            
            if int(shares_v[0]) == shares:
                
                cur.execute("DELETE FROM folio WHERE username = ? AND symbol = ? ;" ,(username,symbol))
                con.commit()
            else:
                cur.execute("UPDATE folio SET shares = shares - ? WHERE username = ? AND symbol = ? ;",(shares,username,symbol))
                con.commit()
            
            return render_template("upstocks.html", smessage = "SOLD")
        
    else:
        
        raws = cur.execute("select * from history where username= ?",(username,))
        raws = list(raws)
        for raw in raws:
            print(raw[3])
        return render_template("upstocks.html")

@app.route("/quote" , methods = ["GET","POST"])
def quote():
    if request.method == "POST":
        symbol= request.form["symbol"]
        symbol = symbol.upper()
        rows = lookup(symbol)
        if not rows:
            return render_template("error.html" , message = "API PROCESS IS NOT WORKING")
        price = rows["price"]
        return render_template("upstocks.html" , qmessage =f" THE PRICE OF {symbol} IS {price}")
    else:
        return render_template("upstocks.html")

@app.route("/history" ,methods = ["GET","POST"])
def history():
    username = str(session.get("userid"))
    history = cur.execute("SELECT symbol,operation,price,shares FROM history WHERE username = ?;",(username,)).fetchall()
    for row in history:
        print(row[0],row[1],row[2],row[3])
        
    
    return render_template("upstocks.html" , stocks = history)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/mail")
def mailf():
   msg = Message('Hello', sender = 'ankurshukla146@gmail.com', recipients = ['jareddunn209@gmail.com'])
   msg.body = "Hello Flask message sent from Flask-Mail"
   mail.send(msg)
   return "Sent"

def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        
        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token=pk_5d243a7263534979996406236217bbcc"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


    
        
