from resources.browsermobproxy import browsermobproxy as mob
from haralyzer import HarParser
import json
import os
from selenium import webdriver
import chartify
import pandas as pd
import getopt
import sys
import concurrent.futures
import time
import logging


def check_service_in_har(har_data, service_name):
    logging.info('Checking for service -->'+ service_name)
    har_parser = HarParser(json.loads(har_data))
    for x in har_parser.har_data['entries']:
        if x['request']['url'] == service_name:
            logging.info('got service -> '+service_name)
            return True

def generate_har(test, runconfig, service_list):
    if runconfig == 'browsermobproxy':
        path = os.path.join(os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir)),
                            'resources')

        BROWSERMOB_PROXY_PATH = path + '/driver/browsermob-proxy/browsermob-proxy'
        url = test['testurl']

        s = mob.Server(BROWSERMOB_PROXY_PATH)
        s.start()
        proxy = s.create_proxy()
        proxy_address = "--proxy=127.0.0.1:%s" % proxy.port
        service_args = [proxy_address, '--ignore-ssl-errors=yes', ]
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument("--proxy-server={0}".format(proxy.proxy))
        driver = webdriver.Chrome(chrome_options=options, service_args=service_args, executable_path=path + '/driver/chromedriver')
        # driver = webdriver.PhantomJS(service_args=service_args)
        proxy.new_har(url)
        driver.get(url)
        import time
        time.sleep(10)
        har_data = json.dumps(proxy.har, indent=4)

        # wroite logic to wait for all the services to be in har file
        # for x in service_list:
        #     condition = False
        #     logging.info('Going to look into har for service -->'+ x)
        #     while not condition:
        #         if check_service_in_har(har_data, x):
        #             condition = True
        #         else:
        #             logging.warning('Didn\'t find service -->'+x)
        #             condition = False
        #             har_data = json.dumps(proxy.har, indent=4)

        driver.quit()
        s.stop()
        return har_data
    else:
        return None

def save_har(har_data, testname):
    harname = os.path.join(os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir)),
                        'temp', testname+'.har')

    if os.path.exists(harname):
        os.remove(harname)
    save_har = open(harname, 'x')
    save_har.write(har_data)
    save_har.close()

def save_har_to_csv(test, testname, service_list, desc_list):
    import csv
    harname = os.path.join(os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir)),
                           'temp', testname+'.har')
    csv_name = os.path.join(os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir)),
                           'temp', testname+'.csv')
    if os.path.exists(csv_name):
        os.remove(csv_name)
    with open(harname, 'r') as f:
        har_parser = HarParser(json.loads(f.read()))
        with open(csv_name, mode='x') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',', lineterminator='\n')
            csv_writer.writerow(['desc','url','status', 'response_type','time', 'starttime'])
            for x in har_parser.har_data['entries']:
                    if x['request']['url'] in service_list:
                        desc = desc_list[service_list.index(x['request']['url'])]
                        url = x['request']['url']
                        status = x['response']['status']
                        time = x['time']
                        start = x['startedDateTime']
                        csv_writer.writerow([desc, url, status, 'actual', time, start])
            #write expected to csv
            for x in test['api']:
                csv_writer.writerow([x['description'],  x['servicename'], x['status_code'], 'expected', x['expectedresponseinms'], 0])
    return csv_name

def generate_chart(csv_name, testname, format):
    tidy_data = pd.read_csv(csv_name)
    data = (tidy_data.groupby(
        ['desc', 'response_type'])['time'].sum().reset_index())

    ch = chartify.Chart(blank_labels=True, x_axis_type='linear', y_axis_type='categorical')
    ch.set_title("Page Performance Test")
    ch.set_subtitle("Response Graph for --> "+testname)
    ch.plot.bar(
        data_frame=data,
        categorical_columns=['desc', 'response_type'],
        numeric_column='time',
        color_column='desc',
        # categorical_order_by='labels',
        categorical_order_ascending=True
    )

    ch.plot.text(
        data_frame=data,
        categorical_columns=['desc', 'response_type'],
        numeric_column='time',
        text_column='time',
        color_column='desc',
        # categorical_order_by='labels'
    )
    ch.axes.set_xaxis_label('Time in (ms) --->')
    ch.axes.set_yaxis_label('APIs --->')
    ch.style.set_color_palette('categorical', 'Dark2')
    ch.axes.set_xaxis_tick_orientation('horizontal')
    ch.axes.set_yaxis_tick_orientation('horizontal')
    ch.set_legend_location(None)
    ch.show()
    filename = csv_name.replace('.csv', '.html')
    if os.path.exists(filename):
        os.remove(filename)
    ch.save(filename, format)

def get_list(test, filter):
    list = []
    for x in test['api']:
        list.append(x[filter])
    return list

def thread_initiate(test, build, runconfig, project):
    service_list = get_list(test, 'servicename')
    desc_list = get_list(test, 'description')
    hardata = generate_har(test, runconfig, service_list)
    if hardata is None:
        raise Exception('Failed to generate Har data')
    testname = test['testname'].replace(' ', '').lower()
    save_har(hardata, testname)
    csv_name = save_har_to_csv(test, testname, service_list, desc_list)
    # TODO write method to make pass/fail judgement
    # TODO push to ES
    # TODO push to manta
    generate_chart(csv_name, testname, 'html')

def execute(f, b, t, r, p):
    from time import gmtime
    st_time = gmtime()
    path = (
        os.path.join(os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir)),
                     'temp', f))

    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    import json
    with open(path) as json_file:
        test_to_execute = json.load(json_file)

    if t == 'any':
        t = len(test_to_execute)
    else:
        t = int(t)

    with concurrent.futures.ThreadPoolExecutor(max_workers=t) as executor:
        future_to_url = {executor.submit(thread_initiate, t, b, r, p): t for t in test_to_execute}

        for future in concurrent.futures.as_completed(future_to_url):
            t = future_to_url[future]
            try:
                future.result()
            except Exception as exc:
                logging.error('%r generated an exception: %s' % (t, exc))

    # single execution
    # for i in range(len(test_to_execute)):
    #         thread_initiate(test_to_execute[i], b, r, p)
    en_time = gmtime()
    logging.info('total execution time: ' + str(time.mktime(en_time) - time.mktime(st_time)))

def main(argv):
    path = (
        os.path.join(os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir)),
                     'temp', 'page_test.log'))
    logging.basicConfig(level=logging.DEBUG, filename=path, filemode='w', format='%(name)s - %(levelname)s - %(message)s')

    filename = None
    buildnumber = None
    threads = None
    runconfiguration = None
    project = None

    try:
        opts, args = getopt.getopt(argv, "f:b:t:r:p:",
                                   ["filename=", "buildnumber=", "threads=", "runconfiguration=",
                                    "project="])
    except getopt.GetoptError:
        logging.error(
            'main.py -f <filename> -b <buildnumber> -t <threads> -r <run configuration> -p <project>')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            logging.warning(
                'main.py -f <filename> -b <buildnumber> -t <threads> -r <run configuration> -p <project>')
            sys.exit()
        elif opt in ("-f", "--filename"):
            filename = arg
        elif opt in ("-b", "--buildnumber"):
            buildnumber = arg
        elif opt in ("-t", "--threads"):
            threads = arg
        elif opt in ("-r", "--runconfiguration"):
            runconfiguration = arg
        elif opt in ("-p", "--project"):
            project = arg
    arglist = [filename, buildnumber, threads, runconfiguration, project]
    if None in arglist:
        raise Exception('Correct the command line arguments, item missing!!!')
    execute(filename, buildnumber, threads, runconfiguration, project)

if __name__ == '__main__':
    main(sys.argv[1:])
