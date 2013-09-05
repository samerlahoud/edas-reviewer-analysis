from lxml import etree
import re
from bs4 import BeautifulSoup
from collections import OrderedDict, Counter

results_file_date = 'bilan-edas-2-9-13'
html_results_file = open(results_file_date+'.html')
results = html_results_file.read()

paper_dict_per_pID={}

# Dict format is conf={Total_review_length, Total_nb_reviewers, Paper_list}
paper_dict_per_conf={}

html_components = re.finditer('<html(.+?)/html>', results)

for html_instance in html_components: 
	soup = BeautifulSoup(html_instance.group()) 
	html_table = soup.findAll("table")[0]
	rows = html_table.findChildren(['th', 'tr'])
	for row in rows:
		cells = row.findChildren('td')
		values = [cell.string for cell in cells]
		if values:
			# If the paper with the same ID is already in the dict, then mash it
			paper_dict_per_pID[values[5]]=[values[0], values[1], values[2], values[3], values[4]]
			
			# If conference exists
			if paper_dict_per_conf.has_key(values[0]):
				# If this is not the first paper for an existing conference
				if values[5] not in paper_dict_per_conf[values[0]][2]:
					# Add the paper to the list
					paper_dict_per_conf[values[0]][2].append(values[5])
					
					# Update the number of papers
					#nb_papers = len(paper_dict_per_conf[values[0]][2])
					
					# Update the total review length
					paper_dict_per_conf[values[0]][0] = int(paper_dict_per_conf[values[0]][0])+int(values[1])
					
					# Update the number of reviewers
					paper_dict_per_conf[values[0]][1] = int(paper_dict_per_conf[values[0]][1])+int(values[2])
					
					# Update the mean review length			
					#paper_dict_per_conf[values[0]][2] = int(paper_dict_per_conf[values[0]][0]/paper_dict_per_conf[values[0]][1])
			else:
				paper_dict_per_conf[values[0]]=[int(values[1]), int(values[2]), [values[5]]]	

#print paper_dict_per_pID
#print paper_dict_per_conf

# Get an ordered dictionary for publications sorted by mean review length
publication_ordered_dict = OrderedDict(sorted(paper_dict_per_conf.items(), key=lambda t: t[1][2]))

# Open a CSV file and write the review analysis and close it automatically below
with open(results_file_date+'.csv', 'w') as f:
	f.write('Conference Name, Mean Review Length per Reviewer, Mean Number of Reviewers per Paper\n')
	l = []
	
	# Iterate over items returning key, value tuples
	for k, v in publication_ordered_dict.iteritems():
		if v[1]:
			mean_review_length_per_reviewer = v[0]/v[1]
		else:
			mean_review_length_per_reviewer = 0
		mean_nb_reviewrs_per_paper = v[1]/len(v[2])
		
		# Build a nice list of strings
		l.append('%s, %s, %s' % (str(k), mean_review_length_per_reviewer, mean_nb_reviewrs_per_paper)) 
		
	# Join that list of strings and write out
	f.write('\n'.join(l))                    