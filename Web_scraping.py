# Importing Useful libraries
from selenium import webdriver
from PIL import Image
import pytesseract
from io import BytesIO
from bs4 import BeautifulSoup as Soup
import sqlite3
#from selenium.webdriver.chrome.options import Options
import time

# set path of tesseract
pytesseract.pytesseract.tesseract_cmd = r'F:\SOFT\tessreact\tesseract.exe'

class Gtu:
    def __init__(self):
        print("Object Created")

    # Method to store data in local database
    def store_in_db(self, database_path, enrollment, name, CPI, SPI, current_block, Total_back):
        # Making Connection with local database
        conn = sqlite3.connect(database_path)
        # Making object of cursor to execute all SQL queries
        c = conn.cursor()

        # creating table if not exist
        c.execute('''CREATE TABLE IF NOT EXISTS results(enrollment real PRIMARY KEY, name text,
                   CPI real, SPI real, Current_Backlog text, Total_Backlog text)''')

        # Insert a row of data
        insert_query = f"INSERT OR IGNORE INTO results VALUES (?, ?, ?, ?, ?, ?)"
        c.execute(insert_query, (enrollment, name, CPI, SPI, current_block, Total_back))

        conn.commit()
        conn.close()

    # Method To take screenshot of captcha code box for further processing
    def screenshot(self, driver):
        element = driver.find_element_by_id('imgCaptcha')  # find part of the page you want image of
        location = element.location
        size = element.size
        png = driver.get_screenshot_as_png()  # saves screenshot of entire page

        im = Image.open(BytesIO(png))  # uses PIL library to open image in memory

        left = location['x']
        top = location['y']
        right = location['x'] + size['width']
        bottom = location['y'] + size['height']

        im = im.crop((left, top, right, bottom))  # defines crop points
        # im.save('captcha/{}.png'.format((enrollment + no)))  # saves new cropped image
        # im = Image.open('captcha/{}.png'.format((enrollment + no)))  # opening image into memory
        return im

    # img = cv2.imread('{}.png'.format(enrollment[0]), 0)

    # Method for converting image into thresholding image
    def binirize(self, image_to_transform, threshold):
        image = image_to_transform.convert("L")
        w = image.width
        h = image.height
        for x in range(w):
            for y in range(h):
                if image.getpixel((x, y)) < threshold:
                    image.putpixel((x, y), 0)
                else:
                    image.putpixel((x, y), 255)
        return image

    # Method for removing horizontal line from Captcha of thresholded image and applying OCR
    def text_captcha(self, captcha_image):
        new_size = (captcha_image.width * 3, captcha_image.height * 3)
        bigcaptcha = captcha_image.resize(new_size)
        img = self.binirize(bigcaptcha, 150)
        w = img.width
        # h = img.height
        # remove black line from captcha(which lie on pixel 52 to 58 in vertical direction)
        for y in range(67, 72):
            for x in range(0, w):
                if img.getpixel((x, y - 1)) < 100:
                    continue
                img.putpixel((x, y), 255)
        # display(img)
        return pytesseract.image_to_string(img)

    # Main Method & is called
    def main(self):
        before = time.time()

        #chrome_options = Options()
        #chrome_options.add_argument('--headless')

        # Chrome Driver for selenium put your driver path
        driver = webdriver.Chrome("F:\SOFT\chrome webdriver\chromedriver")
        # Accessing gtu result web site
        driver.get("https://www.gturesults.in/Default.aspx?ext=W2020&rof=2716&ext=W2020&rof=2716")
        # https://www.gturesults.in/Default.aspx?ext=archive
        # https://www.gturesults.in/Default.aspx?ext=W2020&rof=2716&ext=W2020&rof=2716
        # Giving Session
        
        ''' session is needed when there is option for selection otherwise not '''
        #session = driver.find_element_by_id('ddlsession')
        # add year as appeared in site
        #session.send_keys('Winter 2020')

        # Entering BE Sem-4 Regular batch
        batch = driver.find_element_by_id('ddlbatch')
        # send your result name as appeared in GTUresult site
        batch.send_keys('.....BE SEM 5 - Regular (JAN 2021)')

        # defining enrollment range
        #put your starting enrollment 
        enrollment = 180170107000
        # {no} represents total number of students
        no = 81

        # count for invalid captcha code trials
        count = 0

        # Extract data of all students untill enrollment reaches to 00
        while (no > 0):
            # Find enrollment box by its attribute id
            enroll = driver.find_element_by_id(
                'txtenroll')  # Don't Use find_elements that will return list and turn into error
            # clear if any previous value is in the box
            enroll.clear()
            time.sleep(2)
            enroll.send_keys(str(enrollment + no))
            print(str(enrollment + no))
            im = self.screenshot(driver)
            text = self.text_captcha(im)

            # entering captcha into box and hit search
            capEnter = driver.find_element_by_id('CodeNumberTextBox')
            # clear if any previous value is in the box
            capEnter.clear()
            # sleep for 2 second
            time.sleep(2)
            capEnter.send_keys(text)

            search = driver.find_element_by_id('btnSearch')

            # store html in content
            content = driver.page_source
            soup = Soup(content, 'html5lib')

            # Extracting msg process status
            msg = soup.find('span', attrs={'id': 'lblmsg'}).text.strip()
            time.sleep(2)

            # If data of student is not available then skip to next enrollment
            if msg == "Oppssss! Data not available.":
                print('Data is not available for Enrollment no:', (enrollment + no))
                no = no - 1
                continue

            # if captcha is wrong then it will run same loop and increase count of wronged attempts
            elif msg == "ERROR: Incorrect captcha code, try again.":
                count += 1
                print(f"Incorrect captcha code count {count}")
                continue

            time.sleep(2)

            # Getting Details
            name = soup.find('span', attrs={'id': 'lblName'}).text.strip()
            try:
                current_block = soup.find('span', attrs={'id': 'lblCUPBack'}).text
            except:
                current_block = 'NA'
            try:
                Total_back = soup.find('span', attrs={'id': 'lblTotalBack'}).text
            except:
                Total_back = 'NA'
            try:
                SPI = soup.find('span', attrs={'id': 'lblSPI'}).text
            except:
                SPI = 0
            try:
                CPI = soup.find('span', attrs={'id': 'lblCPI'}).text
            except:
                print(f"Can't get data for {enrollment + no}")
                CPI = 0
            self.store_in_db("data.db", enrollment + no, name, CPI, SPI, current_block, Total_back)
            print(f"Done storing {enrollment + no}")

            no = no - 1  # To get next student's detail

        driver.delete_all_cookies()
        # Closing driver automatically
        driver.close()
        after = time.time()

        print("Data Extracted \nClosing Browser............\n")
        # Printing Summary of Program
        print("Browser Closed \n Check Database for data")
        print("============Summary=============")
        print(f"Total time taken : {((after - before)/60)} Minutes")
        print(f"Total incorrect captcha : {count}")


gtu = Gtu()
gtu.main()
