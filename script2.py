from flask import Flask, request
import json
import requests


app = Flask(__name__)
    

@app.route('/newCasesPeak')
def newCasesPeak():
    country = request.args.get('country')
    return get(method='newCasesPeak',country=country)

@app.route('/recoveredPeak')
def recoveredPeak():
    country = request.args.get('country')
    return get(method='recoveredPeak',country=country)

@app.route('/deathsPeak')
def deathsPeak():
    country = request.args.get('country')
    return get(method='deathsPeak',country=country)

@app.route('/status')
def status():
    return '''{"status": "success"}'''


@app.context_processor
def get(method,country):
    #covid api info
    base_url = "https://disease.sh/"
    headers = "accept: application/json"

    #user contry of choice
    country = country

    response = requests.get(base_url + f"v3/covid-19/historical/{country}?lastdays=30",headers)

    #checking if country is exsits in the data 
    raw_content = response.content
    if 'country' not in str(raw_content,'utf8'):
        return '{}'

    #convert bytes to json   
    str_content = raw_content.decode('utf8').replace("'", '"')
    response_json = json.loads(str_content)

    #wanted data -> relevant key
    if method == 'newCasesPeak':
        key = 'cases'

    elif method == 'recoveredPeak':
        key = 'recovered'

    elif method == 'deathsPeak':
        key = 'deaths'
        

    #get the relevant arry
    my_query = response_json['timeline'][key]

    #sort the dict by top values
    sort_by_value = ({k: v for k, v in sorted(my_query.items(), key= lambda v: v[0])})

    #get the top (first) key
    keys_view = sort_by_value.keys()
    keys_iterator = iter(keys_view)
    first_key = next(keys_iterator)

    #get the top (first) value
    values_view = sort_by_value.values()
    value_iterator = iter(values_view)
    first_value = next(value_iterator)

    return '''{"country":%s,"method":%s,"date":%s,"value":%s}''' % (country, method, first_key, first_value)


if __name__ == "__main__":
    app.run(debug=True)





