#!/usr/local/bin/python

# This script is written by Samer Lahoud (2013)
# You can call it using: python reviewer_analysis.py edas-login edas-password
# The output is a CSV file with the review statistics of all you submissions

import requests
import re
import sys
from bs4 import BeautifulSoup
from collections import OrderedDict, Counter

# Start a request session
current_session = requests.Session()

# Initialise the payload for the request  
payload={}
payload['username'] = sys.argv[1]
payload['password'] = sys.argv[2]

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
print "You have sumbitted a total of %s papers:" %sum(publication_counter.values())
for publication_item in publication_counter.items():
	print "%s: %s" % (publication_item[0], publication_item[1])

# Get an ordered dictionary for publications sorted by mean review length
publication_ordered_dict = OrderedDict(sorted(publication_dict.items(), key=lambda t: t[1][2]))

# Open a CSV file and write the review analysis and close it automatically below
with open('reviewer_analysis_'+author_id+'.csv', 'w') as f:
	f.write('Conference Name, Total Review Length, Number of Reviewers, Mean Review Length, Paper Status, pID\n')
	l = []
	
	# Iterate over items returning key, value tuples
	for k, v in publication_ordered_dict.iteritems():
	 
		# Silently discard pending or active papers
		if v[3] == 'paper-rejected' or v[3] == 'paper-accepted' or v[3] == 'paper-published':
			# Build a nice list of strings
			l.append('%s, %s, %s, %s, %s, %s' % (str(k), str(v[0]), str(v[1]), str(v[2]), str(v[3]), str(v[4]))) 
	 # Join that list of strings and write out
	f.write('\n'.join(l))                    