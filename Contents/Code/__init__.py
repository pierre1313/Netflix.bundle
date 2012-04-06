import string, netflix, xmlrpclib, mod_xmlrpcTransport, traceback, re, time, os
try:
    from urlparse import parse_qsl
except:
    from cgi import parse_qsl
import htmlentitydefs
import webbrowser

#http://www.netflix.com/XML/U/MovieData?movieid=60036838


NETFLIX_PLUGIN_PREFIX    = "/video/netflix"
#NETFLIX_RPC_HOST         = "http://netflix.plexapp.com:8999"#"http://127.0.0.1:8999"#"http://netflix.plexapp.com:8999"
CACHE_TIME               = 3600
WI_PLAYER_URL            = "http://movies.netflix.com/WiPlayer?movieid=%s"
#WI_PLAYER_URL            = "http://api.netflix.com/catalog/movie/%s"
MOVIE_DETAILS            = "http://api.netflix.com/catalog/titles/movies/%s?format=json"
EPISODE_DETAILS          = "http://api.netflix.com/catalog/titles/programs/%s?format=json"
XML_MOVIE_DETAILS        = "http://www.netflix.com/XML/U/MovieData?movieid=%s"
NETFLIX_SEARCH           = "http://api.netflix.com/catalog/titles"

ODATA_URL                = "http://odata.netflix.com/v2/Catalog/"
ODATA_MOVIE_DETAILS      = ODATA_URL+"/Titles('%s')?$format=json"
ODATA_CAST_DETAILS       = ODATA_URL+"/Titles('%s')/Cast?$format=json"
ODATA_DIRECTORS_DETAILS  = ODATA_URL+"/Titles('%s')/Directors?$format=json"
ODATA_LOOKUP_ID          = "http://odata.netflix.com/v2/Catalog/Titles?$filter=substringof('%s',NetflixApiId)&$format=json"


NETFLIX_ART              = 'art-default.png'
NETFLIX_ICON             = 'icon-default.png'

# functionality options
HOSTED_MODE              = True
ALLOW_SAFE_MODE          = False
VIDEO_IN_BROWSER         = False

ENABLE_V2_API            = False
##

NO_ITEMS                 = MessageContainer('No Results','No Results')
TRY_AGAIN                = MessageContainer('Error','An error has happened. Please try again later.')
ERROR                    = MessageContainer('Network Error','A Network error has occurred')

def hasSilverlight():
    retVal = Platform.HasSilverlight
    if retVal == False:
        Log("trying to find silverlight in other places")
        paths = [
            '/Library/Internet Plug-Ins/Silverlight.plugin',
            os.path.expanduser('~/Library/Internet Plug-Ins/Silverlight.plugin'),
            '/Library/Internet Plug-ins/Silverlight.plugin',
            os.path.expanduser('~/Library/Internet Plug-ins/Silverlight.plugin'),
        ]
        for p in paths:
            if os.path.exists(p):
                Log("found in %s" % p)
                return True
    else:
        Log("found silverlight with Platform.HasSilverlight")
    return retVal


## NEW ##
def Start():
#    try:
#        Data.Remove('userFeedsCached')
#    except:
#        pass

    Plugin.AddPrefixHandler(NETFLIX_PLUGIN_PREFIX, TopMenu, "Netflix", NETFLIX_ICON, NETFLIX_ART)
    Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
    Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')
    MediaContainer.art = R(NETFLIX_ART)
    MediaContainer.ratingColor = "FFEE3725"

    HTTP.Headers["User-agent"] = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_6; en-gb) AppleWebKit/528.16 (KHTML, like Gecko) Version/4.0 Safari/528.16"
    HTTP.CacheTime = 3600
    
    Dict['GlobalNetflixSession'] = None
    
    if not Dict['GlobalNetflixSession']:
        Dict['GlobalNetflixSession']  = NetflixSession()

    clearCaches()

def Thumb(url):
  try:
    data = HTTP.Request(url, cacheTime=CACHE_1WEEK).content
    return DataObject(data, 'image/jpeg')
  except:
    return Redirect(R(NETFLIX_ICON))
    
def CheckThumb(url):
  try:
    data = HTTP.Request(url, cacheTime=CACHE_1WEEK).content
    return True
  except:
    return False

def TopMenu():
    if hasSilverlight() == False:
      return MessageContainer('Error','Silverlight is required for the Netflix plug-in.\nPlease visit http://silverlight.net to install.')

    dir = MediaContainer(disabledViewModes=["Coverflow"], viewGroup="List", title1="Netflix") 

    try:
        if not Dict['GlobalNetflixSession']:
          Dict['GlobalNetflixSession']  = NetflixSession()
        try:
          loggedIn = Dict['GlobalNetflixSession'].loggedIn()
          if not loggedIn:
            Log("attempting login")
            loggedIn = Dict['GlobalNetflixSession'].tryLogin()
        except:
          Log("attempting login")
          loggedIn = Dict['GlobalNetflixSession'].tryLogin()
    except Exception, e:
        Log("Error: %s" % e)
        #return TRY_AGAIN

    try:
      if loggedIn:
        if ENABLE_V2_API == True:
          dir.Append(Function(DirectoryItem(Menu,"Browse Movies", thumb=R("icon-movie.png")), type="Movie"))
          dir.Append(Function(DirectoryItem(Menu,"Browse TV", thumb=R("icon-tv.png")), type="TV"))
        dir.Append(Function(DirectoryItem(UserQueueMenu,"Your Instant Watch Queue", thumb=R("icon-queue.png"))))
        dir.Append(Function(DirectoryItem(RecommendationsMenu,"Recommendations", thumb=R(NETFLIX_ICON))))
        dir.Append(Function(DirectoryItem(ParseRSS , "Top 100", thumb=R(NETFLIX_ICON)), url="http://rss.netflix.com/Top100RSS"))
        dir.Append(Function(DirectoryItem(ParseRSS , "New Instant Watch Releases", thumb=R(NETFLIX_ICON)), url="http://www.netflix.com/NewWatchInstantlyRSS"))
        dir.Append(Function(InputDirectoryItem(SearchMenu,"Search", "Search Netflix", thumb=R("search.png") )))
    except:
        dir.Append(Function(DirectoryItem(FreeTrial,"Sign up for free trial", thumb=R("icon-movie.png"))))
    
#    dir.Append(Function(DirectoryItem(ParseCatalog , "Complete Instant Catalog", thumb=R(NETFLIX_ICON)), url="http://api.netflix.com/catalog/titles/full?v=2.0"))

    dir.Append(PrefsItem(title="Netflix Preferences", thumb=R("icon-prefs.png")))
    dir.nocache = 1

    return dir


def MyRecommendations(sender):
    dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1) 
    try:
        userfeeds = recommendationFeeds()
        for f in userfeeds:
            dir.Append(Function(DirectoryItem(PersonalFeed,f['name'], thumb=R(NETFLIX_ICON)), url=f['url']))
    except:
        pass
    return dir

def FreeTrial(sender):
    url = "http://www.netflix.com/"
    webbrowser.open(url,new=1,autoraise=True)
    return MessageContainer("Free Trial Signup",
"""A browser has been opened so that you may sign up for a free
trial.  If you do not have a mouse and keyboard handy, visit
http://www.netflix.com and sign up for free today!"""
    )
    pass

def PersonalFeed(sender,url=None):
    dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1) 

    Log('PersonalFeed: %s' % url)
    try:
        items = getUserFeed(url)
    except Exception, e:
        Log("TRY_AGAIN: %s" % e)
        return TRY_AGAIN
    if len(items) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows found')
    populateFromCatalog(items,dir)
    if len(dir) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows found')

    return dir


def Menu(sender,type=None):
    if type=='Movie':
        all_icon = 'icon-movie.png'
    elif type == 'TV':
        all_icon = 'icon-tv.png'
    dir = MediaContainer(disabledViewModes=["Coverflow"], viewGroup="List",title1=sender.title1) 
    dir.Append(Function(DirectoryItem(AlphaListMenu,"All %s" % type, thumb=R(all_icon)), type=type))
    dir.Append(Function(DirectoryItem(GenreListMenu,"%s by Genres" % type, thumb=R(NETFLIX_ICON)), type=type))
    dir.Append(Function(DirectoryItem(LanguageListMenu,"%s by Language" % type, thumb=R(NETFLIX_ICON)), type=type))
    dir.Append(Function(DirectoryItem(YearListMenu,"%s by Year" % type, thumb=R("icon-year.png")), type=type))
    dir.Append(Function(DirectoryItem(RatingListMenu,"%s by Rating" % type, thumb=R("icon-recommend.png")), type=type))
    dir.Append(Function(DirectoryItem(ActorListMenu,"All Actors", thumb=R("icon-people.png")), type=type))
    dir.Append(Function(DirectoryItem(DirectorListMenu,"All Directors", thumb=R("icon-people.png")), type=type))
    return dir

def parseMovie(JsonString):
    movie = JSON.ObjectFromString(JsonString)
    try:
      if movie['Instant']['Available'] == True:
       #Log(JSON.StringFromObject(movie))
       summary = movie['ShortSynopsis']
       if summary == None:
         summary = movie['Synopsis']
                                
       try:
          duration = int(movie['Runtime'])*1000
          summary = "Runtime: %s\n\n%s" % (msToRuntime(duration),summary)
          infoLabel = msToRuntime(duration)
       except:
          duration = None
          summary = ''
          infoLabel = None
                  
       if movie['Rating']:
          summary = "Rating: %s\n%s" % (movie['Rating'],summary)
                 
       if CheckThumb(movie['BoxArt']['MediumUrl']) == True:
          thumb = movie['BoxArt']['MediumUrl']
       else:
          thumb = movie['BoxArt']['SmallUrl']
                 
       return(Function(PopupDirectoryItem(
                              InstantMenu,
                              title=movie['Name'],
                              thumb=thumb,#Function(Thumb,url=thumb),
                              summary=summary,
                              duration = duration,
                              userRating = 2*movie['AverageRating'],
                              subtitle = movie['ReleaseYear'],
                              ratingColor = "FFEE3725",
                              infoLabel=infoLabel
                            ),
                            id=movie['Id'],
                            url=movie['NetflixApiId']
                          ))
      else:
        Log("not available in instant watch")
    except:
       #Log(JSON.StringFromObject(movie))
       id = movie['id']
       try:
         movie = movie['item']
       except:
         pass
       try:
         summary = movie['synopsis']['regular']
       except:
         summary = XML.ElementFromURL(XML_MOVIE_DETAILS%id.split('/')[-1]).xpath("//SYNOPSIS")[0].text
       try:
          duration = int(movie['runtime'])*1000
          summary = "Runtime: %s\n\n%s" % (msToRuntime(duration),summary)
          infoLabel = msToRuntime(duration)
       except:
          duration = None
          infoLabel = None
       
       try:
         infoLabel = str(movie['episode_count']) + " ep."
         season_link = movie['links']['episodes']
       except:
         season_link = None
         
       if movie['ratings']:
          summary = "Rating: %s\n%s" % (movie['ratings'],summary)
                 
       if CheckThumb(movie['box_art']['large']) == True:
          thumb = movie['box_art']['large']
       else:
          thumb = movie['box_art']['small']
          
       try:
         title = movie['title']['episode_short']
       except:
         title = movie['title']['short']
        
       if season_link != None:
         return(Function(DirectoryItem(ParseEpisodes,
                         title=title,
                         thumb=thumb,#Function(Thumb,url=thumb),
                         summary=summary,
                         userRating = 2*int(movie['average_rating']),
                         subtitle = movie['release_year'],
                         ratingColor = "FFEE3725",
                         infoLabel=infoLabel
                         ),
                         url=season_link
                         ))
       else:
         return(Function(PopupDirectoryItem(
                              InstantMenu,
                              title=title,
                              thumb=thumb,#Function(Thumb,url=thumb),
                              summary=summary,
                              duration = duration,
                              userRating = 2*int(movie['average_rating']),
                              subtitle = movie['release_year'],
                              ratingColor = "FFEE3725",
                              infoLabel=infoLabel
                            ),
                            id=id,
                            url=movie['id']
                          ))

def ParseEpisodes(sender,url):
    dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, title2=sender.itemTitle) 
    
    r = netflix.NetflixRequest()
    at = Dict['GlobalNetflixSession'].getAccessToken()
    thisUrl = r.make_query(access_token=at,query=url,params={'expand':'synopsis,episodes','output':'json'},method="GET", returnURL=True)
    jsonObj = JSON.ObjectFromURL(thisUrl)
 #   @parallelize  
 #   def iter():    
    for item in jsonObj['episodes']:
 #       @task
 #       def Metadata(item=item):  
          r = netflix.NetflixRequest()
          at = Dict['GlobalNetflixSession'].getAccessToken()
          thisUrl = r.make_query(access_token=at,query=item['id'],params={'expand':'@title,@box_art,@synopsis,@seasons,@formats,@episodes,@episode','output':'json'},method="GET", returnURL=True)
          jsonObj = JSON.ObjectFromURL(thisUrl)
          dir.Append(parseMovie(JSON.StringFromObject(jsonObj['catalog_title']))) 
      
    return dir

def ParseCatalog(sender,url,single=False):
    dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, title2=sender.itemTitle) 
    
    r = netflix.NetflixRequest()
    at = Dict['GlobalNetflixSession'].getAccessToken()
    thisUrl = r.make_query(access_token=at,query=url,params={'expand':'@title,@box_art,@synopsis,@seasons,@formats,@episodes,@episode','output':'json'},method="GET", returnURL=True)
    xmlstr = HTTP.Request(thisUrl).content
    jsonObj = JSON.ObjectFromURL(thisUrl)
    
    if (single == False):
      @parallelize  
      def iter():
        for item in jsonObj['catalog_titles']:
          @task
          def Metadata(item=item):    
            dir.Append(parseMovie(JSON.StringFromObject(item))) 
    else:
      dir.Append(parseMovie(JSON.StringFromObject(jsonObj['catalog_title']))) 

    if dir is None or len(dir) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows available for streaming')
    dir.nocache = 1
    return dir
    
      
def RelatedItem(sender,id):
    dir = MediaContainer(disabledViewModes=["Coverflow"], viewGroup="List", title1=sender.title1, title2="Related",ratingColor = "FFEE3725") 
    dir.Append(Function(DirectoryItem(DirectorListMenu,"Movies from the same director(s)", thumb=R("icon-people.png")), query=(ODATA_DIRECTORS_DETAILS % id)))
    dir.Append(Function(DirectoryItem(ActorListMenu,"Movies with the same actors", thumb=R("icon-people.png")), query=(ODATA_CAST_DETAILS % id)))
    return dir  
      
def AlphaListMenu(sender,type=None,query=None):
    if query is not None:
        # handle a query if one was given
        dir = MediaContainer(disabledViewModes=["Coverflow"], viewGroup="List", title1=sender.title1, title2=query,ratingColor = "FFEE3725") 
        jsonObj = JSON.ObjectFromURL(ODATA_URL+'Titles?$filter=Type%20eq%20%27'+type+'%27%20and%20substring%28Name,0,1%29%20eq%20%27'+query.lower()+'%27&$format=json')
        for movie in jsonObj['d']['results']:
          dir.Append(parseMovie(JSON.StringFromObject(movie)))
    else:
        # list possible queries if none is given
        dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, title2=sender.itemTitle) 
        dir.Append(Function(DirectoryItem(AlphaListMenu,"#","#",thumb=R(NETFLIX_ICON)), type=type, query="#"))
        for letter in ["A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z"]:
            dir.Append(Function(DirectoryItem(AlphaListMenu,"%s" % letter,letter,thumb=R(NETFLIX_ICON)), type=type, query=letter))
    if len(dir) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows found')
    return dir
    
def GenreListMenu(sender,type=None,query=None,level=1):
    GenrePage = HTML.ElementFromURL('http://www.netflix.com/AllGenresList').xpath("//div[@id='genreList']")[0]
    #Log(query)
    if query is None:
      dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, title2=sender.itemTitle) 
      for genre in GenrePage.xpath("//ul[@class='level1']/li/a"):
        #Log(XML.StringFromElement(genre))
        dir.Append(Function(DirectoryItem(GenreListMenu,genre.text, thumb=R(NETFLIX_ICON)), type=type, query=genre.text,level = 1))
    else:
        # list possible queries if none is given
      dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, title2=sender.itemTitle) 
      #Log(level)
      for genre in GenrePage.xpath("//ul[@class='level"+str(level)+"']/li/a"):
        if genre.text == query :
          #Log(XML.StringFromElement(genre.xpath('../..')[0]))
          if not genre.xpath("./../ul[@class='level"+str(level+1)+"']"):
            jsonObj = JSON.ObjectFromURL(ODATA_URL+"Genres('"+String.Quote(query).replace('/','%2F')+"')/Titles?$filter=Type%20eq%20%27"+type+"%27%20&$format=json")
            for movie in jsonObj['d']['results']:
              dir.Append(parseMovie(JSON.StringFromObject(movie)))
          else:
            for genre in GenrePage.xpath("//ul[@class='level"+str(level)+"']/li/a"):
              if genre.text == query:
                for subgenre in genre.xpath("../ul[@class='level"+str(level+1)+"']/li/a"):
                  dir.Append(Function(DirectoryItem(GenreListMenu,subgenre.text, thumb=R(NETFLIX_ICON)), type=type, query=subgenre.text,level=level+1))

    if len(dir) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows available for streaming')
    return dir
    
def LanguageListMenu(sender,type=None,query=None):
    dir = MediaContainer(disabledViewModes=["Coverflow"],viewGroup="List", title1=sender.title1, title2=sender.itemTitle) 
    if query is None:
       for lang in ("English","French","German","Spanish","More Languages"):
        dir.Append(Function(DirectoryItem(LanguageListMenu,lang, thumb=R(NETFLIX_ICON)), type=type, query=lang))
    else:
      if 'More' in query:
        jsonObj = JSON.ObjectFromURL("http://odata.netflix.com/v2/Catalog/Languages?$format=json")
        for lang in jsonObj['d']['results']:
         dir.Append(Function(DirectoryItem(LanguageListMenu,lang['Name'], thumb=R(NETFLIX_ICON)), type=type, query=lang['Titles']['__deferred']['uri']))
      else:
        dir.viewGroup = 'InfoList'
        if 'http' in query:
          jsonObj = JSON.ObjectFromURL(query+'?$filter=Type%20eq%20%27'+type+'%27%20&$format=json')
        else:
          jsonObj = JSON.ObjectFromURL(ODATA_URL+'Languages(%27'+String.Quote(query)+'%27)/Titles?$filter=Type%20eq%20%27'+type+'%27%20&$format=json')
        for movie in jsonObj['d']['results']:
          dir.Append(parseMovie(JSON.StringFromObject(movie)))
    if len(dir) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows available for streaming')
    return dir    

def YearListMenu(sender,type=None,query=None):
    if query is None:
        # handle a query if one was given
        dir = MediaContainer(disabledViewModes=["Coverflow"],viewGroup="List",title1=sender.title1, title2=query) 
        for decade in ["2010's","2000's","1990's","1980's","1970's","1960's","1950's","1940's","1930's","1920's","1910's","1900's"]:
            dir.Append(Function(DirectoryItem(YearListMenu,"%s" % decade,decade, thumb=R(NETFLIX_ICON)), type=type, query=decade))
    else:
        # list possible queries if none is given
        if "'s" in query:
          decade = int(query.split("'s")[0])
          dir = MediaContainer(disabledViewModes=["Coverflow"],viewGroup="List", title1=sender.title1, title2=sender.itemTitle) 
          for y in [9,8,7,6,5,4,3,2,1,0]:
            if (decade+y) <= Datetime.Now().year:
              dir.Append(Function(DirectoryItem(YearListMenu,"%s" % str(decade+y),str(decade+y), thumb=R(NETFLIX_ICON)), type=type, query=str(decade+y)))
        else:
            dir = MediaContainer(disabledViewModes=["Coverflow"],viewGroup="InfoList", title1=sender.title1, title2=sender.itemTitle) 
            jsonObj = JSON.ObjectFromURL(ODATA_URL+'Titles?$filter=Type%20eq%20%27'+type+'%27%20and%20ReleaseYear%20eq%20'+query.lower()+'%20&$format=json')
            for movie in jsonObj['d']['results']:
              dir.Append(parseMovie(JSON.StringFromObject(movie)))        
    if len(dir) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows available for streaming')
    return dir

def RatingListMenu(sender,type=None,query=None):
    if query is None:
        # handle a query if one was given
        dir = MediaContainer(disabledViewModes=["Coverflow"],viewGroup="List", title1=sender.title1, title2=query) 
        for rating in ["5 stars","4 stars","3 stars","2 stars","1 star"]:
            dir.Append(Function(DirectoryItem(RatingListMenu,"%s" % rating,rating, thumb=R(NETFLIX_ICON)), type=type, query=rating))
    else:
        dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, title2=sender.itemTitle) 
        rating = int(query.split(' ')[0])
        if rating == 5:
          jsonObj = JSON.ObjectFromURL(ODATA_URL+'Titles?$filter=Type%20eq%20%27'+type+'%27%20and%20AverageRating%20eq%205%20&$format=json')
        else:
          jsonObj = JSON.ObjectFromURL(ODATA_URL+'Titles?$filter=Type%20eq%20%27'+type+'%27%20and%20AverageRating%20gt%20'+str(rating)+'%20and%20AverageRating%20lt%20'+str(rating+0.99)+'%20&$format=json')
        for movie in jsonObj['d']['results']:
          dir.Append(parseMovie(JSON.StringFromObject(movie)))        
    if len(dir) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows available for streaming')
    return dir

def ActorListMenu(sender,type=None,query=None):
    dir = MediaContainer(disabledViewModes=["Coverflow"],viewGroup="List", title1=sender.title1, title2=sender.itemTitle) 
  
    if query is None:
        jsonObj = JSON.ObjectFromURL(ODATA_URL+'People?$format=json')
        for actor in jsonObj['d']['results']:
          dir.Append(Function(DirectoryItem(ActorListMenu,actor['Name'], thumb=R(NETFLIX_ICON)), type=type, query=str(actor['Id'])))
    else: 
       if 'Cast' in query:
         jsonObj = JSON.ObjectFromURL(query)
         for actor in jsonObj['d']['results']:
           dir.Append(Function(DirectoryItem(ActorListMenu,actor['Name'], thumb=R(NETFLIX_ICON)), type=type, query=str(actor['Id'])))
       else:
         dir.viewGroup="InfoList"
         jsonObj = JSON.ObjectFromURL(ODATA_URL+'People(%s)/TitlesActedIn?$format=json' % query )
         for movie in jsonObj['d']['results']:
           dir.Append(parseMovie(JSON.StringFromObject(movie)))

    if len(dir) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows available for streaming')
    return dir
   
def DirectorListMenu(sender,type=None,query=None):
    dir = MediaContainer(disabledViewModes=["Coverflow"],viewGroup="List", title1=sender.title1, title2=sender.itemTitle) 
    if query is None:
        jsonObj = JSON.ObjectFromURL(ODATA_URL+'People?$format=json')
        for actor in jsonObj['d']['results']:
          dir.Append(Function(DirectoryItem(DirectorListMenu,actor['Name'], thumb=R(NETFLIX_ICON)), type=type, query=str(actor['Id'])))
    else:
      if 'Directors' in query:
         jsonObj = JSON.ObjectFromURL(query)
         for director in jsonObj['d']['results']:
           dir.Append(Function(DirectoryItem(DirectorListMenu,director['Name'], thumb=R(NETFLIX_ICON)), type=type, query=str(director['Id'])))
      else:
        dir.viewGroup="InfoList"
        jsonObj = JSON.ObjectFromURL(ODATA_URL+'People(%s)/TitlesDirected?$format=json' % query)
        for movie in jsonObj['d']['results']:
          dir.Append(parseMovie(JSON.StringFromObject(movie)))
    if len(dir) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows available for streaming')
    return dir

def ChildTitlesMenu(sender,parentId=None,query=None):
    dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, title2=sender.itemTitle) 

    try:
        childTitles = getChildrenOfTitle(parentId)
    except Exception, e:
        Log("TRY_AGAIN: %s" % e)
        return TRY_AGAIN

    dir = populateFromCatalog(childTitles, dir)
    if len(dir) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows available for streaming')
    return dir
    
def ParseRSS(sender,url, replaceParent=False):    
  dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, title2=sender.itemTitle) 
    
  r = netflix.NetflixRequest()
  at = Dict['GlobalNetflixSession'].getAccessToken()
#    instant_url = 'http://api.netflix.com/users/%s/queues/instant' % at.user_id
  @parallelize  
  def iter():
    for movie in XML.ElementFromURL(url).xpath('//channel/item/link'):
      @task
      def Metadata(movie=movie):
        id = movie.text.split('/')[-1]
        if '?' in id:
          id = id.split('?')[0]
        try:
          #jsonObj = JSON.ObjectFromURL(ODATA_LOOKUP_ID%id)['d']['results'][0]
          #dir.Append(parseMovie(jsonstring))
          thisUrl = r.make_query(access_token=at,query=MOVIE_DETAILS%id,params={'output':'json'},method="GET", returnURL=True)
          jsonObj = JSON.ObjectFromURL(thisUrl)
          dir.Append(parseMovie(JSON.StringFromObject(jsonObj['catalog_title']))) 
        except:
          pass  
  if dir is None or len(dir) == 0:
      return MessageContainer(sender.itemTitle,'No movie or TV shows available for streaming')
  dir.nocache = 1
  return dir

def UserQueueMenu(sender,max=50,start=0,replaceParent=False):
  dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, title2=sender.itemTitle) 
    
  r = netflix.NetflixRequest()
  at = Dict['GlobalNetflixSession'].getAccessToken()
  instant_url = 'http://api.netflix.com/users/%s/queues/instant' % at.user_id
  thisUrl = r.make_query(access_token=at,query=instant_url,params={'expand':'@title,@box_art,@synopsis,@seasons,@formats,@episodes,@episode','output':'json'},method="GET", returnURL=True)
  jsonObj = JSON.ObjectFromURL(thisUrl)
  
  @parallelize  
  def iter():   
    for item in jsonObj['queue']:
      @task
      def Metadata(item=item):
        dir.Append(parseMovie(JSON.StringFromObject(item))) 

  if dir is None or len(dir) == 0:
    return MessageContainer(sender.itemTitle,'No movie or TV shows available for streaming')
  return dir
    
def RecommendationsMenu(sender,replaceParent=False):
  dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, title2=sender.itemTitle) 

  r = netflix.NetflixRequest()
  at = Dict['GlobalNetflixSession'].getAccessToken()
  recommend_url = 'http://api.netflix.com/users/%s/recommendations' % at.user_id
  thisUrl = r.make_query(access_token=at,query=recommend_url,params={'output':'json'},method="GET", returnURL=True)
  Log(HTTP.Request(thisUrl))
  jsonObj = JSON.ObjectFromURL(thisUrl)
  
  @parallelize  
  def iter():     
    for item in jsonObj['recommendations']:
      @task
      def Metadata(item=item):
       dir.Append(parseMovie(JSON.StringFromObject(item))) 
         
  if dir is None or len(dir) == 0:
    return MessageContainer(sender.itemTitle,'No movie or TV shows available for streaming')
  return dir

def SearchMenu(sender, query=None):
  dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, title2=query) 

  r = netflix.NetflixRequest()
  at = Dict['GlobalNetflixSession'].getAccessToken()
  thisUrl = r.make_query(access_token=at,query=(NETFLIX_SEARCH),params={'term':query,'output':'json','max_results':'25'},method="GET", returnURL=True)
  jsonObj = JSON.ObjectFromURL(thisUrl)

  @parallelize  
  def iter():
    for title in jsonObj['catalog_item']:
      @task
      def Metadata(title=title):
        id = title['id'].split('/')[-1]
        try:
          thisUrl = r.make_query(access_token=at,query=MOVIE_DETAILS%id,params={'output':'json'},method="GET", returnURL=True)
          jsonObj = JSON.ObjectFromURL(thisUrl)
          dir.Append(parseMovie(JSON.StringFromObject(jsonObj['catalog_title'])))
        except:
          pass

  if len(dir) == 0:
    return MessageContainer('Search','No titles available for streaming')
  return dir

def parseCatalogTitle(item):

    try:
        href = item.xpath(".//id/text()")[0]
    except:
        href = ''

    parts = href.split('/')
    type = parts[5]
    id   = parts[-1]
    if parts[-2] == 'seasons':
        type = 'seasons'

    try:
        synopsis = item.xpath('.//synopsis/text()')[0]
        synopsis = re.sub(r'<[^>]+>','',synopsis)
    except:
        synopsis = ''

    try:
        runtime = item.xpath('.//runtime/text()')[0]
    except:
        runtime = '0'

    title = ''
    try:
        title = item.xpath(".//title")[0].get('short')
    except:
        pass
    episode_title = ''
    try:
        episode_title = item.xpath(".//title")[0].get('episode_short')
    except:
        pass
    if episode_title:
        title = episode_title

    BOX_ART_PREFS = [
        'http://schemas.netflix.com/catalog/titles/box_art.hd.iw',
        'http://schemas.netflix.com/catalog/titles/box_art.hd',
        'http://schemas.netflix.com/catalog/titles/box_art.large',
        'http://schemas.netflix.com/catalog/titles/box_art.medium',
        'http://schemas.netflix.com/catalog/titles/box_art.small'
    ]
    box_art = ''
    try:
        art_options = {}
        arts = item.xpath(".//box_art/link")
        for o in arts:
            art_options[ o.get('rel') ] = o.get('href')
        for o in BOX_ART_PREFS:
            if o in art_options:
                box_art = art_options[o]
                break
    except Exception, e:
        pass

    rating = '0.0'
    try:
        rating = item.xpath(".//average_rating")[0].text
    except:
        pass

    delivery_formats = {}
    for i in item.xpath(".//category[@scheme='http://api.netflix.com/categories/title_formats']"):
        delivery_formats[ str(i.attrib['label']).lower() ] = True

    actors = [ i.attrib for i in item.xpath(".//link[@rel='http://schemas.netflix.com/catalog/people.cast']/people/link") ]
    directors = [ i.attrib for i in item.xpath(".//link[@rel='http://schemas.netflix.com/catalog/people.directors']/people/link") ]
    series = [ i.attrib for i in item.xpath(".//link[@rel='http://schemas.netflix.com/catalog/title.series']") ]
    seasons = [ i.attrib for i in item.xpath(".//link[@rel='http://schemas.netflix.com/catalog/title.season']") ]
    genres = [ i.attrib for i in item.xpath(".//category[@scheme='http://api.netflix.com/categories/genres']") ]

    parent_href = ''
    if type == 'programs':
        if len(seasons) >= 1:
            parent_href = seasons[0]['href']
        elif len(series) >= 1:
            parent_href = series[0]['href']
        else:
            logging.error("Expecting at least one season or series link for: %s" % href)
            logging.error(xml)
            parent_href = 'BAD_HREF'

        pass
    elif type == 'seasons':
        if len(series) == 0:
            logging.error("Expecting a series link for: %s" % href)
            logging.error(xml)
            parent_href = 'BAD_HREF'
        else:
            parent_href = series[0]['href']




    parsed = {}
    parsed['title'] = title
    parsed['type']  = type
    parsed['movieId'] = id
    parsed['nf_synopsis'] = synopsis
    parsed['nf_duration'] = runtime
    parsed['mpaa_tv_rating'] = rating
    parsed['href'] = href
    parsed['parent_href'] = parent_href
    parsed['nf_boxart'] = box_art
    parsed['nf_rating'] = rating
    parsed['delivery_formats'] = delivery_formats
  
    try:
        parsed['release_year'] = item.xpath('.//release_year')[0].text
    except:
        parsed['release_year'] = ''

    try:
        parsed['nf_tv_rating'] = item.xpath(".//category[@scheme='http://api.netflix.com/categories/tv_ratings']")[0].get('label')
    except:
        parsed['nf_tv_rating'] = ''

    try:
        parsed['nf_mpaa_rating'] = item.xpath(".//category[@scheme='http://api.netflix.com/categories/mpaa_ratings']")[0].get('label')
    except:
        parsed['nf_mpaa_rating'] = ''

    return parsed

def massageTitleInfo(id):

  if ENABLE_V2_API == True:
    t = JSON.ObjectFromURL(ODATA_LOOKUP_ID%id)['d']['results'][0]
    Log(t)

    item = {
        'id': id,
        'movieId': t['Id'],
        'type': t['Type'],
        'title': t['Name'],
        'subtitle': t['ReleaseYear'],
        'thumb': t['BoxArt']['LargeUrl'],
        'summary': t['Synopsis'],
        'art': '',
        'duration': int(t['Runtime'])*1000,
        'is_instant': t['Instant']['Available'],
        'rating': t['Rating'],
        'rating_user': float(t['AverageRating']),
        'mpaa_tv_rating': t['Rating'],
        'url': WI_PLAYER_URL % id,
        'href': "",
        'parent_href': "",
    }
  else:
    r = netflix.NetflixRequest()
    at = Dict['GlobalNetflixSession'].getAccessToken()
    try:
      url = r.make_query(access_token=at,query=MOVIE_DETAILS%id,params={'output':'json','expand':'synopsis'},method="GET", returnURL=True)
      t = JSON.ObjectFromURL(url)['catalog_title']
      Log(t)
    except:
      url = r.make_query(access_token=at,query=EPISODE_DETAILS%id,params={'output':'json','expand':'synopsis'},method="GET", returnURL=True)
      t = JSON.ObjectFromURL(url)['catalog_title']
      Log(t)
    
      
    try:
      summary = t['synopsis']
    except:
      summary = XML.ElementFromURL(XML_MOVIE_DETAILS%t['id'].split('/')[-1]).xpath("//SYNOPSIS")[0].text
    
    try:
      runtime = int(t['runtime'])*1000
    except:
      runtime = None
      
    item = {
        'id': t['id'],
        'movieId': t['id'],
        'type': 'Movie',#t['Type'],
        'title': t['title']['regular'],
        'subtitle': t['release_year'],
        'thumb': t['box_art']['large'],
        'summary': summary,
        'art': '',
        'duration': runtime,
        'is_instant': 'True',#t['Instant']['Available'],
        'rating': t['ratings'],
        'rating_user': float(t['average_rating']),
        'mpaa_tv_rating': t['ratings'],
        'url': WI_PLAYER_URL % id,
        'href': "",
        'parent_href': "",
    }
  return item

def msToRuntime(ms):

    if ms is None or ms <= 0:
        return None

    ret = []

    sec = int(ms/1000) % 60
    min = int(ms/1000/60) % 60
    hr  = int(ms/1000/60/60)

    return "%02d:%02d:%02d" % (hr,min,sec)


def InstantMenu(sender, url='', id = None):
    Log(url)
    if 'programs' in url:
      item = massageTitleInfo(url.split('/')[-2])
    else:
      item = massageTitleInfo(url.split('/')[-1])

    dir = MediaContainer(title1="Options",title2=sender.itemTitle,disabledViewModes=["Coverflow"], httpCookies=HTTP.CookiesForURL('http://www.netflix.com/'))

    madeWebVid = False
    r = netflix.NetflixRequest()
    at = Dict['GlobalNetflixSession'].getAccessToken()
    #url = 'http://api.netflix.com/users/%s/title_states' % at.user_id
    #res = r.make_query(access_token=at,query=url,params={'title_refs': item['href']},method="GET", returnURL=False)
    #Log(res.read())
    
    if item['type'] in ['programs','Movie']:
        bookmark = 0
        try:
            r = netflix.NetflixRequest()
            at = Dict['GlobalNetflixSession'].getAccessToken()
            url = 'http://api.netflix.com/users/%s/title_states' % at.user_id
            res = r.make_query(access_token=at,query=url,params={'title_refs': item['href']},method="GET", returnURL=False)
            #xmlStr = res.read()
            xml = XML.ElementFromURL(res)
            bookmark = int(xml.xpath('//playback_bookmark/text()')[0])  
        except Exception, e:
            Log(e)
            pass

        bookmark = bookmark * 1000
        Log(bookmark)

        if bookmark > 0:
            wvi = makeWebvideoItem(item)
            wvi.title = "Restart Video"
            dir.Append(wvi)
            wvi = makeWebvideoItem(item,mode='resume')
            wvi.title = "Resume Video - %s" % msToRuntime(bookmark)
            dir.Append(wvi)
        else:
            wvi = makeWebvideoItem(item)
            wvi.title = "Play Video"
            dir.Append(wvi)
        madeWebVid = True
    else:
        summary = item['summary']
        if item['type'] != 'programs' and item['duration'] > 0:
            summary = "Runtime: %s\n%s" % (msToRuntime(item['duration']),summary)
        if item['mpaa_tv_rating']:
            summary = "Rating: %s\n%s" % (item['mpaa_tv_rating'],summary)
        infoLabel = msToRuntime(item['duration'])
        dirItem = Function(
            DirectoryItem(
                ChildTitlesMenu,
                "View Episodes",
                summary=summary,
                thumb=item['thumb'],
                art='',
                subtitle=item['subtitle'],
                duration=item['duration'],
                infoLabel=infoLabel,
                rating=item['rating'],
                userRating=item['rating_user'],
                ratingKey=item['href'],
            ),
            parentId=item['href']
         )
        dir.Append(dirItem)

  #  if item['type'] != 'programs':
  #      if videoIsInQ(item):
  #          dir.Append(Function(DirectoryItem(QueueItem,"Remove from Instant Queue",thumb=R("icon-queue.png")),add="0",url="%s"%item['href']))
  #      else:
  #          dir.Append(Function(DirectoryItem(QueueItem,"Add to Instant Queue",thumb=R("icon-queue.png")),add="1",url="%s"%item['href']))

    if (id != None) and ENABLE_V2_API:
      dir.Append(Function(DirectoryItem(RelatedItem,"Related Items",thumb=R("icon-queue.png")),id = id ))

    if madeWebVid:
        dir.nocache = 1
    if len(dir) == 0:
        return MessageContainer(sender.itemTitle,'No movie or TV shows found')
    return dir

def QueueItem(sender,add='',url=''):
    Log("QueueItem: add: %s url: %s" % (add,url))
    add = int(add)

    item = massageTitleInfo(url.split('/')[-1])

    title = "Success"
    vidInQ = videoIsInQ(item)
    res = None
    Dict['inInstantQ'] = {}
    if add:
        if vidInQ:
            title = "Error"
            message = "Title already in your Instant Queue"
        else:
            message = "Title added to your Instant Queue"
            try:
                r = netflix.NetflixRequest()
                at = Dict['GlobalNetflixSession'].getAccessToken()
                params = {
                    'title_ref': item['href']
                }
                url = 'http://api.netflix.com/users/%s/queues/instant' % at.user_id
                res = r.make_query(access_token=at,query=url,params=params,method="POST", returnURL=False)
            except Exception, e:
                Log(e)
                title = "Error"
                message = "There was a problem adding this title to your Instant Queue"
    else:
        if not vidInQ:
            title = "Error"
            message = "Title is not in your Instant Queue"
        else:
            message = "Title removed from your Instant Queue"
            url = vidInQ['id']
            r = netflix.NetflixRequest()
            at = Dict['GlobalNetflixSession'].getAccessToken()
            try:
                res = r.make_query(access_token=at,query=url,method="DELETE", returnURL=False)
            except Exception, e:
                Log(e)
                title = "Error"
                message = "There was a problem removing this title from your Instant Queue"

    if res is not None and res.status >= 400:
        title = "Error"
        if res.status == 400 and add:
            message = """There are too many items in your Queue. You
will need to remove some before you can add
any more"""
        else:
            message = "Try again..."

    return MessageContainer(title,message)

def getPlayerUrl(url='',mode='restart'):
    if not HOSTED_MODE or ( ALLOW_SAFE_MODE and Prefs['safemode'] ):
        return url

    Log("building movie url")
    Log(url)
    at = Dict['GlobalNetflixSession'].accessToken
    try:
      url,p = url.split('?')
    except: 
      p = url.split('/')[-1]
    movieId = p.split('=')[-1]
    userUrl = "http://api.netflix.com/users/%s" % (at.user_id)
    Log("user id: %s" % at.user_id)
    Log("user url: %s" % userUrl)

    params = {
        'movieid': movieId,
        'user': userUrl
    }
    Log("params: %s" % repr(params))
    Log("raw url : %s",url)
    r = netflix.NetflixRequest()
    url = r.make_query(access_token=at,query=url,params=params,method="GET", returnURL=True)
    Log("final url built: %s" % repr(url))

#     name 	= Dict['GlobalNetflixSession'].getUsername()
#     password = Dict['GlobalNetflixSession'].getPassword()
#     accept_tos 	='TRUE'
#     application_name ='Plex'
#     oauth_consumer_key 	= Dict['GlobalNetflixSession'].getConsumerKey()
#     oauth_token 	= str(Dict['GlobalNetflixSession'].getAccessToken()).split('oauth_token=')[-1]
#     oauth_callback = url
#     
#     final_url = 'https://api-user.netflix.com/oauth/login?name=%s&password=%s&accept_tos=%s&application_name=%s&oauth_consumer_key=%s&oauth_token=%s&oauth_callback=%s'%(name,
#     password,
#     accept_tos,
#     application_name,
#     oauth_consumer_key,
#     oauth_token,
#     oauth_callback)
    
    #final_url = url + '&oauth_token='+str(Dict['GlobalNetflixSession'].getAccessToken()).split('oauth_token=')[-1]+'&fcId=true'

    return "%s#%s" % (url,mode)


def BuildPlayerUrl(sender,url='',mode='restart',forcePlay=False,setCookiePref=False):

    if setCookiePref:
        Prefs['cookieallow'] = True

    cookieallow = Prefs['cookieallow']
    if cookieallow or forcePlay:
        url = getPlayerUrl(url,mode)

        key = WebVideoItem(url).key
        key = key[:16] + key[16:].replace('.','%2E')
        Log("NEW KEY: " + key)
         
        if VIDEO_IN_BROWSER:
          webbrowser.open(url,new=1,autoraise=True)
        else:
          return Redirect(WebVideoItem(url))
            #return Redirect(key)
    else:
        return CookieWarning(sender,url,mode)

def NoInstantAvailable(sender,url,mode):
    return MessageContainer('Sorry','This title is no longer available for instant watch')

def CookieWarning(sender,url,mode):
    dir = MediaContainer(disabledViewModes=["Coverflow"], title1=sender.title1, noHistory=True) 
    dir.Append(
        Function(WebVideoItem(
            BuildPlayerUrl,
            "Allow Cookie Once",
            summary="Netflix would like to set a cookie.  Is this OK?",
            thumb=R(NETFLIX_ICON)
        ),url=url,mode=mode,forcePlay=True)
    )
    dir.Append(
        Function(WebVideoItem(
            BuildPlayerUrl,
            "Yes, Don't Ask Again",
            summary="Allow Netflix to set cookies and don't ask this again",
            thumb=R(NETFLIX_ICON)
        ),url=url,mode=mode,forcePlay=True,setCookiePref=True)
    )
    return dir


def makeWebvideoItem(item={},mode='restart'):
    cookieallow = Prefs['cookieallow']
    summary = item['summary']
    if item['type'] != 'programs' and item['duration'] > 0:
        summary = "Runtime: %s\n%s" % (msToRuntime(item['duration']),summary)
    if item['mpaa_tv_rating']:
        summary = "Rating: %s\n%s" % (item['mpaa_tv_rating'],summary)
    if item['is_instant'] is False:
        infoLabel = msToRuntime(item['duration'])
        Log(item['url'])
        wvi = Function(DirectoryItem(
            NoInstantAvailable,
            item['title'],
            summary=summary,
            subtitle=item['subtitle'],
            duration=item['duration'],
            infoLabel=infoLabel,
            thumb=item['thumb'],
            art=item['art'],
            rating=item['rating'],
            userRating=item['rating_user'],
            ratingKey=item['href'],
        ),url="%s"%item['url'],mode=mode)
    elif cookieallow:
        wvi = Function(WebVideoItem(
            BuildPlayerUrl,
            item['title'],
            summary=summary,
            subtitle=item['subtitle'],
            duration=item['duration'],
            thumb=item['thumb'],
            art=item['art'],
            rating=item['rating'],
            userRating=item['rating_user'],
            ratingKey=item['href'],
        ),url="%s"%item['url'],mode=mode)
    else:
        infoLabel = msToRuntime(item['duration'])
        wvi = Function(DirectoryItem(
            CookieWarning,
            item['title'],
            summary=summary,
            subtitle=item['subtitle'],
            duration=item['duration'],
            infoLabel=infoLabel,
            thumb=item['thumb'],
            art=item['art'],
            rating=item['rating'],
            userRating=item['rating_user'],
            ratingKey=item['href'],
        ),url="%s"%item['url'],mode=mode)

    return wvi

##
# http://effbot.org/zone/re-sub.htm#unescape-html
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

def clearCaches():
    Data.Remove('userFeedsCached')
    Dict['ratingCache']         = {}
    Dict['quickCache']          = {}
    Dict['inInstantQ']          = {}
    Dict['instantUrl']          = None

class NetflixSession():
    def __init__(self):
        self.TOKEN_KEY = 'accesstoken'
        self.username = Prefs["loginemail"]
        self.password = Prefs["password"]
        pass

    def getAccessToken(self):
        tok = Data.LoadObject(self.TOKEN_KEY)
        if tok != None:
            tok.app_name = 'Plex'
        return tok
    def setAccessToken(self, tokObj):
        if tokObj == None:
            Data.Remove(self.TOKEN_KEY)
        else:
            Data.SaveObject(self.TOKEN_KEY,tokObj)
    def delAccessToken(self):
        self.setAccessToken(tokObj=None)
    accessToken = property(fget=getAccessToken,fset=setAccessToken,fdel=delAccessToken)
  
    def getConsumerKey(self):
      return netflix.CONSUMER_KEY

    def getUsername(self):
        return Prefs["loginemail"]
    def setUsername(self,user):
        if user != self.getUsername():
            self.setAccessToken(None)
        Prefs["loginemail"] = user
    def delUsername(self):
        self.setUsername(user=None)
    username = property(fget=getUsername,fset=setUsername,fdel=delUsername)

    def getPassword(self):
        return Prefs["password"]
    def setPassword(self,password):
        if password != self.getPassword():
            self.setAccessToken(None)
        Prefs["password"] = password
    def delPassword(self):
        self.setPassword(password=None)
    password = property(fget=getPassword,fset=setPassword,fdel=delPassword)

    def refreshCredentials(self):
        if self.username != Prefs["loginemail"]:
            clearCaches()
            self.username = Prefs["loginemail"]
            self.setAccessToken(tokObj=None)

        if self.password != Prefs["password"]:
            clearCaches()
            self.password = Prefs["password"]
            self.setAccessToken(tokObj=None)

        return True

    def loggedIn(self):
        self.refreshCredentials()
        ret = self.getAccessToken() != None
        if not ret and Data.Load('login_converted') is None:
            self.tryLogin()
            Data.Save('login_converted','True')
            ret = self.getAccessToken() != None
        if ret:
            Log('checking access token validity')
            r = netflix.NetflixRequest()
            at = self.getAccessToken()
            if at is not None:
                url = 'http://api.netflix.com/users/%s' % at.user_id
                res = r.make_query(access_token=at,query=url,method="GET", returnURL=False)
                if res.status == 401:
                    Log('access token was found to be revoked: 401')
                    self.setAccessToken(tokObj=None)
                    return False

        return ret

    def tryLogin(self):
        Log("tryLogin()")
        self.refreshCredentials()
        u = self.getUsername()
        p = self.getPassword()

        if u == '' or u is None or p == '' or p is None:
            return False

        try:
            r = netflix.NetflixRequest()
            reqToken = r.get_request_token()

            values =  {'nextpage': 'http://www.netflix.com/',
                      'SubmitButton': 'Click Here to Continue',
                      'movieid': '',
                      'trkid': '',
                      'email': u,
                      'password1': p,
                      'RememberMe': 'True'}
            x = HTTP.Request('https://www.netflix.com/Login', values, cacheTime=0).content

            origParams = {'oauth_callback': '', 'oauth_token': reqToken.key, 
                        'application_name':'Plex', 'oauth_consumer_key':netflix.CONSUMER_KEY,
                        'accept_tos': 'checked', 'login': u, 'password': p,'x':'166','y':'13'}
            x = HTTP.Request("https://api-user.netflix.com/oauth/login", origParams, cacheTime=0).content
            xml = HTML.ElementFromString(x)

            errFound = None
            try:
                errFound = xml.xpath('//p[@id="error"]/text()')[0]
                Log(errFound)
            except:
                pass

            if errFound:
                Log("Netflix responded with an error: %s" % errFound)
                Log("Your username/pass are probably wrong")
                Log(".. or you're using an input method")
                Log(".. which seem to be causing character problems.")
                Log(".. Some things which have caused problems are:")
                Log("     -- using VNC to enter user/pass")
                Log("     -- Rowmote in some cases")
                return False

            at = r.get_access_token(reqToken)
            self.setAccessToken(at)
            if not at:
                return False
            else:
                return True
        except Exception, e:
            Log("(error) '%s' repr(%s)" % (e,repr(e)))
            return False
