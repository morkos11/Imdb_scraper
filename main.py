import requests
import threading
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time
import json
from random import randint
class ImdbBot:
    def __init__(self):
        self.proxy_cnt = 0
    def get_proxy(self):
        with open('proxies.txt','r') as file :
            proxies = file.readlines()
        ip, port, user, password = proxies[self.proxy_cnt].replace('\n','').split(':')
        self.proxy_cnt += 1
        if self.proxy_cnt >= len(proxies):
            self.proxy_cnt = 0
        return ip+':'+port, user, password
    def extract_content(self,content,id):
        try:
            soup = BeautifulSoup(content,'html.parser')
            title_year = soup.find('h3',{'itemprop':"name"}).text.split('(')
            basic_data = soup.findAll('ul',{"class":"ipl-inline-list"})
            try:
                poster = soup.find('img',{"itemprop":"image"})['src']
                poster = poster.split('_V1')[0]+'jpg'
            except:
                poster = 'https://kkkkkz.com/assets/img/poster_no.png'
            title = title_year[0].strip()
            year = int(title_year[-1].replace(')','').replace('-','').strip())
            if year < 1950 :
                return 0

            type = basic_data[0].findAll('li')[-1].text.strip()
            try:
                release_date = basic_data[0].findAll('li')[-2].text.strip()
            except:
                release_date = ''
            try:
                voters = int(basic_data[1].find('span',{"class":"ipl-rating-star__total-votes"}).text.replace('(','').replace(')','').replace(',',''))
                rate = float(basic_data[1].find('span',{"class":"ipl-rating-star__rating"}).text)
            except:
                return 0
            cast_table = soup.find('table',{'class':'cast_list'})
            cast = []
            if cast_table == None:
                return 0
            else:
                cast_table = cast_table.findAll('tr')
                for tr in cast_table:
                    try:
                        tds = tr.findAll('td')
                        name = tds[0].find('img')['title']
                        try:
                            image = tds[0].find('img')['loadlate']
                        except:
                            image = tds[0].find('img')['src']
                        if image == 'https://m.media-amazon.com/images/S/sash/N1QWYSqAfSJV62Y.png' :
                            image = 'https://kkkkkz.com/assets/img/actor.png'
                        else:
                            image = image.split('_V1')[0]+'jpg'
                        cast.append({"name":name,"image":image})
                    except Exception as e:
                        pass
            genres = []
            story = ''
            runtime = ''
            country = ''
            labels = soup.findAll('tr',{'class':"ipl-zebra-list__item"})
            for label in labels :
                if label.find('td').text == 'Genres' :
                    ul = label.find('ul',{'class':"ipl-inline-list"})
                    for genre in ul.findAll('li') :
                        genres.append(genre.text.strip())
                elif label.find('td').text == "Plot Summary" :
                    story = label.find('p')
                    try:
                        story.find('em').extract()
                    except:
                        pass
                    story = story.text.strip().replace('\n','')
                elif label.find('td').text == "Runtime" :
                    runtime = int(label.find('li').text.strip().replace('min',''))
                elif label.find('td').text == "Country" :
                    country = label.find('li').text.strip()
            if len(story) > 0:
                try:
                    ar_story = GoogleTranslator(source='en', target='ar').translate(story)
                except:
                    ar_story = "لا يوجد قصة"

                story = {
                    'en':story,
                    'ar':ar_story
                }
            else:
                story = {
                    'en': 'No plot summary',
                    'ar': 'لا يوجد ملخص قصة'
                }

            if not any(char.isdigit() for char in release_date) :
                release_date = f'{year} ({country})'

            wanted_types = ['movie','short','show','tv mini series','tv movie','tv series']
            wanted_genres = ['action','adult','adventure','animation','biography','comedy','crime','documentary','drama','family','fantasy',
                             'film noir','game show','history','horror','music','musical','mystery','news',None,'reality-tv','romance',
                             'sci-fi','short','sport','talk-show','thriller','war','western','war','western']
            if type.lower() not in wanted_types:
                return 0

            temp_genres = genres
            for g in temp_genres :
                if g.lower() not in wanted_genres:
                    genres.remove(g)


            data = {
                'type':type,
                'genres':genres,
                'title':title,
                'story':story,
                'posters':[poster],
                'rating':rate,
                'raters_count':voters,
                'country_of_origin':country,
                'release_year':year,
                'release_date':release_date,
                'cast':cast
            }
            return data
        except Exception as e:
            with open('errors.txt' , 'a') as file:
                file.write(f'{id}:{str(e)}\n\n')
            return 0
    def write_json(self,movie_data):
        listObj = []
        with open("data.json") as fp:
            listObj = json.load(fp)
        listObj.append(movie_data)

        with open("data.json", "w") as json_file:
            json.dump(listObj, json_file,
                      indent=4,
                      separators=(",", ": "))
    def insert_api(self,movie_data):
        param = json.dumps(movie_data)
        headers = {"Content-Type": "application/json", "Accept": "application/json", "charset": "utf-8"}
        try:
            r = requests.post("https://kkkkkz.com/api/entertainment/create", data=param, headers=headers)
            if r.status_code == 200 :
                print(f'Successfully add {movie_data["title"]}')
            elif r.status_code != 200 and r.status_code != 422:
                print(f'Failed add {movie_data["title"]}')
                self.write_json(movie_data)
        except:
            print(f'Failed add {movie_data["title"]}')
            self.write_json(movie_data)
    def get_movie(self,id):
        server, user, password = self.get_proxy()
        url = f'https://www.imdb.com/title/tt{id}/reference'
        while True:
            proxy = f'http://{user}:{password}@{server}'
            proxies = {'http': proxy, 'https': proxy}
            try:
                req = requests.get(url,proxies=proxies)
                break
            except:
                print(f'Failed to connect with {server}')
                server, user, password = self.get_proxy()
        params = self.extract_content(req.content,id)
        if params != 0:
            self.insert_api(params)


if __name__ == '__main__':
    with open("last_id.txt", "r") as f:
        last_id = f.readline()
    id = int(last_id.replace("\n", ""))
    blank_id = "0000000"
    entries = int(input('Enter number of requests at name time: '))
    threads = []
    bot = ImdbBot()
    while True:
        for i in range(entries):
            str_id = str(id)
            new_id = blank_id[0:-len(str_id)]
            new_id += str_id
            t = threading.Thread(target=bot.get_movie, args=(new_id,))
            id += 1
            threads.append(t)
            t.start()
            time.sleep(0.05)
            with open("last_id.txt", "w") as f:
                f.write(str(id))

        for t in threads:
            t.join()

        sleeping_time = randint(10,20)
        print(f"Sleeping {sleeping_time} seconds")
        time.sleep(sleeping_time)
