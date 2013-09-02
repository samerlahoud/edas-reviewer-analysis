import webapp2
import cgi
import re
import sys
import urllib
from bs4 import BeautifulSoup
from collections import OrderedDict, Counter
from google.appengine.api import mail
import requests

# The handler function that generates the main page 
def mainPage(request):
    return webapp2.Response("""<!doctype html>
<html lang="en">
 <head> <meta charset="utf-8">
   <title>EDAS Analyser</title>
 </head>
 <body>
   <h1>Reviewer Analysis</h1>
   <p>This web application scans your conference submissions on EDAS and produces statistics on the paper reviews such as the number of reviewers, the mean review length, ...</p>
   <h3>Enter your EDAS information:</h3>
   <form action="fetch_edas" method="post">
     <table>
       <tr>
         <th>Login</th>
         <td><input type="text" name="login" /></td>
       </tr>
       <tr>
         <th>Password</th>
         <td><input type="password" name="password" /></td>
       </tr>
     </table>
     <input type="submit" value="Go!" />
     <p>Fetching statistics may take some minutes, ...</p>
   </form>
 </body>
</html>
""")

def fetch_edas(request):
	login = request.params.get('login')
	password = request.params.get('password')
	reply = webapp2.Response("""<!doctype html><html lang="en"><head> <meta charset="utf-8"><title>Review results</title></head><body><h1>Reviewer Analysis</h1>""")
	
	# Start a request session
	current_session = requests.Session()

	# Initialise the payload for the request  
	payload={}
	payload['username'] = login
	payload['password'] = password

	# Get the page with all the papers
	conf_list_request = current_session.post('https://edas.info/listConferencesAuthor.php?past=1', data=payload)
	conf_list_soup = BeautifulSoup(conf_list_request.text)

	# Get the author ID from the title of the page 
	author_id = re.findall(r'\d+', conf_list_soup.title.string)[0]
	
	# Get all links to papers
	paper_refs = conf_list_soup.find_all(title="Show paper", href=True)

	# Initialise the publication dictionary: 
	# key = conference short name, value = (total review length, total nb reviewers, mean review length, paper status, pID)
	publication_dict = {}
			
	for l in paper_refs:
		# Get the paper page
		# Verify = True if SSL problem
		conf_request = current_session.get('https://edas.info/'+l['href'], verify=True)
		conf_soup = BeautifulSoup(conf_request.text)
		pID = re.findall(r'\d+', l['href'])[0]
		
		# Get the status of the paper
		paper_status_tag = conf_soup.find('td', text=re.compile(r'Status'))
		paper_status = paper_status_tag.get('class')[0]
		page_title = conf_soup.title.string

		# Get the conference title
		# findall returns a list, so we take the first element and transform it into a string
		conference_short_title = str(re.findall(r"\[(.*?)\]", page_title)[0])
		conference_short_title = re.sub(r'[,-]', ' ', conference_short_title)

		# Find all review text tags
		review_text_tags = conf_soup.find_all("div", "reviewtext")

		# Find all reviewers tags
		reviewer_tags = conf_soup.find_all("dl", "review")
		total_nb_reviewers = len(reviewer_tags)
		total_review_length = 0
		for i in range(len(review_text_tags)):
			total_review_length = total_review_length + len(str(review_text_tags[i]))
		if total_nb_reviewers:
			mean_review_length = total_review_length/total_nb_reviewers
		else:
			mean_review_length = 0
		publication_dict[conference_short_title] = [total_review_length, total_nb_reviewers, mean_review_length, paper_status, pID]

	# Get a counter of publications	sorted per status
	publication_counter = Counter([x[3] for x in publication_dict.values()])
	
	# Do some pretty printing
	reply.write("<h2>Summary Results</h2>You have sumbitted a total of %s papers:<br>" %sum(publication_counter.values()))
	for publication_item in publication_counter.items():
		reply.write("* %s: %s<br>" % (publication_item[0], publication_item[1]))
		
	# Get an ordered dictionary for publications sorted by mean review length
	publication_ordered_dict = OrderedDict(sorted(publication_dict.items(), key=lambda t: t[1][2]))
	
	reply.write('<br><h2>Detailed Results</h2><p>Results are sorted by mean review length.</p><table border="1"><tr><th>Conference Name</th> <th>Total Review Length</th> <th>Number of Reviewers</th> <th>Mean Review Length</th> <th>Paper Status</th> <th>pID</th></tr>')
	l = []
	
	# Iterate over items returning key, value tuples
	for k, v in publication_ordered_dict.iteritems():
		# Silently discard pending or active papers
		if v[3] == 'paper-rejected' or v[3] == 'paper-accepted' or v[3] == 'paper-published':
			# Build a nice list of strings
			l.append('<tr><td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td></tr>' % (str(k), str(v[0]), str(v[1]), str(v[2]), str(v[3]), str(v[4]))) 
	# Join that list of strings and write out
	output_table = ''.join(l)+'</table>'
	reply.write(output_table)
	reply.write("</body></html>")
	
	message = mail.EmailMessage(sender="samer@lahoud.fr", subject="Review for author %s" %author_id)
	message.to = "samer@lahoud.fr"
	message.body = str(reply)
	message.send()
	
	return reply

# The web application
app = webapp2.WSGIApplication([('/', mainPage),('/fetch_edas', fetch_edas)],debug=True)