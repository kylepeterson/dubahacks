import os
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, BadRequest
import urllib2
import xml.dom
import string
import random
import json
from BeautifulSoup import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

STOP_WORDS = []
f = open('stop_words.txt')
for l in f:
   STOP_WORDS.append(l.strip())
   STOP_WORDS.append(string.join(l.split("'"), ""))
STOP_WORDS = set(STOP_WORDS)

def isMeaningful(word):
   return not (word.lower() in STOP_WORDS or word.startswith('@') or word.startswith('#'))

def recursiveStrip(tweet):
   soup = BeautifulSoup(unicode(tweet))
   return ''.join([e for e in soup.recursiveChildGenerator() if isinstance(e,unicode)])

def getRandQuery(tweet):
   words = tweet.split()
   goodWords = filter(isMeaningful, words)
   return random.choice(words if len(words) == 0 else goodWords)

class SearchService(object):
   def get_query(self, request):
      while True:
         try:
            query = request.args['query']
         except:
            return BadRequest('include a query, dingus')
         contents = urllib2.urlopen(self.twitterBaseURL + query).read()
         soup = BeautifulSoup(contents)
         tweets = soup.findAll('p', { 'class' : 'js-tweet-text tweet-text' })
         pics = soup.findAll('img', { 'class' : 'avatar js-action-profile-avatar' })
         tweets = map(recursiveStrip, tweets)

         json = []
         i = 0
         for tweet in tweets:
            json.append({'text': tweet, 'query': getRandQuery(tweet), 'pic': pics[i]['src']})
            i += 1

         tweets = filter(lambda tweet : tweet['query'].isalpha(), json)
         return self.render_template('results.txt', results=json)

   def get_photo(self, request):
      photoData = json.loads(urllib2.urlopen("http://flickr.com/services/rest/?method=flickr.photos.search&api_key=9a87335e0794d030aac4c2eace643149&text=" + request.args['word'] + "&per_page=1&content_type=1&media=photos&format=json").read()[14:].strip(')'))["photos"]["photo"][0]
      return Response("https://farm" + str(photoData["farm"]) + ".staticflickr.com/" + str(photoData["server"]) + "/" + str(photoData["id"]) + "_" + str(photoData["secret"]) + "_z.jpg")

   """
   dispatch requests to appropriate functions above
   """
   def __init__(self):
      template_path = os.path.join(os.path.dirname(__file__), 'templates')
      self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                           autoescape=False)
      self.url_map = Map([
         Rule('/', endpoint='otherwise'),
         Rule('/query', endpoint="query"),
         Rule('/photo', endpoint="photo"),
      ])
      self.twitterBaseURL = 'https://twitter.com/search?q='

   def render_template(self, template_name, **context):
      t = self.jinja_env.get_template(template_name)
      return Response(t.render(context), mimetype='text/plain')

   def wsgi_app(self, environ, start_response):
      request = Request(environ);
      response = self.dispatch_request(request);
      return response(environ, start_response);

   def __call__(self, environ, start_response):
      return self.wsgi_app(environ, start_response)

   def dispatch_request(self, request):
      adapter = self.url_map.bind_to_environ(request.environ)
      try:
         endpoint, values = adapter.match()
         return getattr(self, 'get_' + endpoint)(request, **values)
      except HTTPException, e:
         return e

   def get_otherwise(self, request):
      return Response('lol wut u doin')
