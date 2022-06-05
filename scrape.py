import argparse, csv, codecs
from facebook_scraper import get_posts
from json import load
from datetime import datetime
from os.path import exists
from os import getcwd

# Useful tool for parsing command line arguments.
# For more info: python scrape.py -h
parser = argparse.ArgumentParser(description='Scrapes facebook post comments and stores them as a csv')
# option to specify an input file that uses the same format as the example, defaults to 'input.json' now
parser.add_argument('-input', type=str, help='Path to the input json', default = 'input.json', nargs = '?')
# option to specify a credentials file that uses the same format as the example, defaults to 'credentials.json'
parser.add_argument('-cred', type=str, help='Path to the credentials json', default = 'credentials.json', nargs = '?')
args = parser.parse_args()

# to be the header of csv file
FORMAT = ['comment','comment_id','comment_time','post','post_id','post_time']
# default max number of pages to request from facebook
MAX_PAGES = 100
# default max number of comments to collect from a post
MAX_COMMENTS = 1000
#default cut off date, after which posts aren't looked at
START_DATE = [2022, 1, 1] # Year, Month, Day

# makes a file name, then appends an incremental integer as long as the file name isn't available.
def csv_file_name(page):
    file_name = f"{page}_comments.csv"
    file_num = 0
    while exists(file_name):
        file_num = file_num + 1
        file_name = f"{page}_comments ({file_num}).csv"
    return file_name

# Uses a csv writer to make append new lines of csv (containing the relevant info) to the file
def csv_comments(page, max_comments, start_date, end_date, credentials, pages):
    print(f"Now scraping '{page}'.")
    file_name = csv_file_name(page)
    with codecs.open(file_name, 'w', encoding='utf-8') as csv_f:
        writer = csv.writer(csv_f)
        writer.writerow(FORMAT)
        # try, except in case a page doesn't exist, or credentials are lacking
        try:
            for post in get_posts(page, pages=pages, credentials=credentials, options={"comments": True, "posts_per_page": 200}):
                post_time = post['time']
                # if posts made before the cut off time are found, stop for this page
                if post_time < start_date: break
                if post_time <= end_date:
                    # new lines break csv, so they're replaced with a hyphen
                    post_text = post['text'].replace('\n', ' - ')
                    post_id = post['post_id']
                    for comment in post['comments_full'][:max_comments]:
                        comment_time = comment['comment_time']
                        comment_text = comment['comment_text']
                        comment_id = comment['comment_id']
                        # with all the relevant information reached and stored, save it to the csv file
                        writer.writerow([post_text, post_id, post_time, comment_text, comment_id, comment_time])
        except:
            print(f"Failed to scrape '{page}'")
            return

# parses the information found in the input file
# using default saves you time in that you don't need to specify information for each page, but are still free to do so
def form_page_prefs(defaults, page):
    if "max_comments" not in page:
        max_comments = defaults['max_comments']
    else:
        max_comments = page['max_comments']
    if "start_date" not in page:
        start_date = defaults['start_date']
    else:
        start_date = page['start_date']
    # may not be datetime if using an input file, is otherwise
    if not isinstance(start_date, datetime):
        start_date = datetime(*[int(d) for d in start_date.split()])
    if "end_date" not in page:
        end_date = defaults['end_date']
    else:
        end_date = page['end_date']
    # may not be datetime if using an input file, is otherwise
    if not isinstance(end_date, datetime):
        end_date = datetime(*[int(d) for d in end_date.split()])
    return (page['page'], max_comments, start_date, end_date)

def set_prefs(is_default=False):
    prefs = {}
    # Lets the user enter a cut off date and maximum number of comments to collect, defaulting if the provided the wrong input 
    s_date = input("Start date for scraping (YYYY MM DD): ")
    e_date = input("End date for scraping (YYYY MM DD): ")
    try: 
        # first split the date into YYYY, MM, DD (based on spaces in text) then convert those three values into ints, and unpack the list containing them for the datetime function to use.
        start_date = datetime(*[int(d) for d in s_date.split()])
        prefs["start_date"] = start_date
    except:
        # If the input wasn't accepted, uses default values if required
        # if is_default:
        start_date = datetime(*START_DATE)
        print(f"Incorrect date format, defaulting to {START_DATE}.")
        prefs["start_date"] = start_date
    try: 
        # first split the date into YYYY, MM, DD (based on spaces in text) then convert those three values into ints, and unpack the list containing them for the datetime function to use.
        end_date = datetime(*[int(d) for d in e_date.split()])
        if end_date < prefs["start_date"]:
            print("End date cannot be before start date.")
            raise Exception()
        prefs["end_date"] = end_date
    except:
        # If the input wasn't accepted, uses default values if required
        # if is_default:
        custom_end_date = [start_date.year, start_date.month + 1, start_date.day]
        end_date = datetime(*custom_end_date)
        print(f"Invalid end date will default to one month after start date. {custom_end_date}.")
        prefs["end_date"] = end_date

    try:
        # converting it to an int may cause an error
        max_comments = int(input("Maximum number of comments: "))
        # raises an error if max_comments is less than 0
        if max_comments < 0:
            raise()
        prefs["max_comments"] = max_comments
    except:
        # If the input wasn't accepted, uses default values if required
        # if is_default:
        max_comments = MAX_COMMENTS
        print(f"Incorrect input, defaulting to {MAX_COMMENTS} comments.")
        prefs["max_comments"] = max_comments
    
    return prefs

def main():
    # tries to find the credentials file, or defaults to no credentials. May not work with certain pages
    try: 
        with open(args.cred) as f:
            credentials = load(f)
        # if the credentials file isn't formatted correctly, raise an exception
        if 'email' not in credentials or 'pass' not in credentials:
            raise Exception("Wrong format for credentials.json")
        # extract only the email and password here
        credentials = credentials.values() 
        print(f"Credentials file '{args.cred}' found.")
    except:
        print(f"'{args.cred}' not found.\nAttempting connections without credentials.")
        credentials = None

    # Doing the same thing as with the credentials now, args.input defaults to 'input.json' even if the user didn't pass in a file-name
    try:
        with open(args.input) as f:
            pages_input = load(f)
        # if the input file isn't formatted correctly (shallow check), raise an exception
        if 'defaults' not in pages_input or 'pages' not in pages_input:
            raise Exception("Wrong format for input.json")
        print(f"Input file '{args.input}' found.")
    except:
        print(f"'{args.input}' file not found.\nDefaulting to manual page info entry.")
        pages_input = None
        
    if pages_input:
        # defaults in case some pages weren't filled out completely 
        defaults = pages_input['defaults']
        pages = pages_input['pages']
        for page in pages:
            # takes the default values for any pages missing information
            page, max_comments, start_date, end_date = form_page_prefs(defaults, page)
            # for each page, save its comments into a csv file for the page
            csv_comments(page, max_comments, start_date, end_date, credentials, MAX_PAGES)


    # if an input file wasn't specified, allow the user to manually enter the pages to search and other information used for the search
    else:
        # Get the default values, in case options are missing/incorrect
        print("\nEnter the default values for the collection.")
        defaults = set_prefs(is_default=True)
        print("\nInput the pages' info. \nEnter with a blank page name to stop. Start/End dates and Max comments are optional here.")
        # Get page names and preferances
        pages = []
        while True:
            page_name = input("Name of page to scrape: ")
            if not page_name: break
            page = set_prefs(is_default=False)
            page["page"] = page_name
            pages.append(page)
        # for each page, save its comments into a csv file for the page
        for page in pages:
            # takes the default values for any pages missing information
            page, max_comments, start_date, end_date = form_page_prefs(defaults, page)
            csv_comments(page, max_comments, start_date, end_date, credentials, MAX_PAGES)

if __name__ == '__main__':
    main()   
    print("Done scraping.")
