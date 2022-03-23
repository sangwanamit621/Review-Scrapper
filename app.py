# Importing necessary Libraries
from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen as ureq
import pymongo

app = Flask(__name__)  # initialising the flask app with the name 'app'

# This function will load home page to get user input
@app.route('/', methods=['GET'])
def homepage():
    return render_template('index.html')

# This function will scrap data from the website if reviews of product are not present in database and show in another html page
@app.route('/scrap',methods=['POST']) # route with allowed methods as POST and GET
def index():
    if request.method == 'POST':
        searchstring = request.form['content'].replace(" ", "")  # obtaining the search string entered in the form
        reviews = [] # To store the reviews in dictionary which will be passed to html page
        try:
            # Establishing connection with mongodb database
            client = pymongo.MongoClient(
                "mongodb+srv://amitsangwan:aCvPKOlLvAjw2dkQ@reviewscrapper.yogd0.mongodb.net/ReviewScrapper?retryWrites=true&w=majority")
            db = client['ReviewScrapper']  # creating cursor for database

            # To create collection in mongodb. collection in MongoDB = table in SQL
            try:
                db.create_collection(f"{searchstring}")
                print("Collection created successfully")
            except:
                print("Collection already exists")

            collections = db[f"{searchstring}"]  # creating cursor for collection

            length = collections.count_documents({})
            if length > 10:
                db_reviews = collections.find({})
                for review in db_reviews:
                    name = review["Name"]
                    rating = review["Rating"]
                    commentHead = review["CommentHead"]
                    custComment = review["Comment"]
                    review_detail = {"Product": searchstring, "Name": name, "Rating": rating,
                                     "CommentHead": commentHead,
                                     "Comment": custComment}  # saving that detail to a dictionary
                    reviews.append(review_detail)

            else:
                # Use scrapping code here
                flipkart_url = "https://www.flipkart.com/search?q=" + searchstring
                uclient = ureq(flipkart_url)
                flipkartpage = uclient.read()
                uclient.close()
                flipkart_html = bs(flipkartpage, "html.parser")
                bigboxes = flipkart_html.findAll("div", {"class": "_1AtVbE col-12-12"})
                del bigboxes[0:3]
                box = bigboxes[0]
                productlink = "https://www.flipkart.com" + box.div.div.div.a['href']

                prodres = requests.get(productlink)
                prod_html = bs(prodres.text, "html.parser")
                allreviews = prod_html.find("div", {"class": "col JOpGWq"})
                total_pages = int(int(allreviews.find("div", {"class": '_3UAT2v _16PBlm'}).text[4:-8]) / 10) + 2
                linker = "https://www.flipkart.com" + allreviews.findAll("a")[-1][
                    'href']  # +"&page=3" # to get link of all reviews

                for i in range(1, total_pages):
                    fulllink = linker + f"&page={i}"
                    openlink = requests.get(fulllink)
                    openlinkhtml = bs(openlink.text, "html.parser")
                    commentboxes = openlinkhtml.find_all('div', {'class': "_27M-vq"})

                    #  iterating over the comment section to get the details of customer and their comments
                    for commentbox in commentboxes:
                        try:
                            name = commentbox.div.div.find_all('p', {'class': '_2sc7ZR _2V5EHH'})[0].text
                        except:
                            name = 'No Name'

                        try:
                            rating = commentbox.div.div.div.div.text
                        except:
                            rating = 'No Rating'

                        try:
                            commentHead = commentbox.div.div.div.p.text
                        except:
                            commentHead = 'No Comment Heading'

                        try:
                            comtag = commentbox.div.div.find_all('div', {'class': 't-ZTKy'})
                            custComment = comtag[0].find("div", {"class": ""}).text
                        except:
                            custComment = 'No Customer Comment'

                        mydict = {"Product": searchstring, "Name": name, "Rating": rating, "CommentHead": commentHead,
                                  "Comment": custComment}  # saving that detail to a dictionary
                        reviews.append(mydict)

                    try:
                        collections.insert_many(reviews, ordered=False)
                    except:
                        continue

            client.close()  # to close the connection with MongoDB server
            return render_template('results.html', reviews=reviews)  # showing the review to the user
        except Exception as error :
            return f'something is wrong : {error}'


if __name__ == "__main__":
    app.run(port=8000, debug=True)

