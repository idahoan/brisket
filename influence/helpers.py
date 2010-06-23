import re
import string
import api
from util import catcodes

def standardize_politician_name(name):
    no_party = strip_party(name)
    proper_case = convert_case(no_party)
    right_order = convert_to_standard_order(proper_case)

    return right_order

def strip_party(name):
    return re.sub(r'\s*\(\w+\)\s*$', '', name)

def convert_case(name):
    if not re.search(r'[A-Z][a-z]', name):
        return string.capwords(name)
    else:
        return name

def convert_to_standard_order(name):
    if '&' in name:
        return convert_running_mates(name)
    else:
        return convert_name_to_first_last(name)

def convert_name_to_first_last(name):
    split = name.split(',')
    if len(split) == 1: return split[0]

    trimmed_split = [ x.strip() for x in split ]

    trimmed_split.reverse()
    return ' '.join(trimmed_split)

def convert_running_mates(name):
    mates = name.split('&')
    fixed_mates = []
    for name in mates:
        fixed_mates.append(convert_name_to_first_last(name))

    return ' & '.join(fixed_mates).strip()

def industry_detail(request, entity_id):
    cycle = request.GET.get("cycle", DEFAULT_CYCLE)
    entity_info = api.entity_metadata(entity_id, cycle)
    top_industries = api.pol_sectors(entity_id, cycle)

    sectors = {}
    for industry in top_industries:
        industry_id = industry['category_name']
        results = api.org_industries_for_sector(entity_id, industry_id)
        sectors[industry_id] = (results)

    return render_to_response('industry_detail.html',
                              {'entity_id': entity_id,
                               'entity_info': entity_info,
                               'sectors': sectors,
                               },
                              entity_context(request, cycle))


# lobbying
def lobbying_by_industry(lobbying_data):
    ''' aggregates lobbying spending by industry'''
    amt_by_industry = {}
    for transaction in lobbying_data:
        industry = transaction['client_category']
        amount = transaction['amount']
        amt_by_industry[industry] = amt_by_industry.get(industry, 0) + int(float(amount))
    # sort into a list of (sector_code, amt) tuples
    z = zip(amt_by_industry.keys(), amt_by_industry.values())
    z.sort(_tuple_cmp, reverse=True)
    # add in the industry and area names
    # return tuples now contain (industry_code, industry_name, industry_area, amt)
    annotated = []
    for item in z:
        code = item[0]
        industry = catcodes.industry_area[item[0].upper()][0]
        sub_industry = catcodes.industry_area[item[0].upper()][1]
        amount = item[1]
        annotated.append((code, industry, sub_industry, amount))
    return annotated

def lobbying_by_customer(lobbying_data):
    amt_by_customer = {}
    for transaction in lobbying_data:
        #if not transaction['registrant_is_firm']:
        #    continue
        customer = transaction['client_name']
        amount = transaction['amount']
        amt_by_customer[customer] = amt_by_customer.get(customer, 0) + int(float(amount))
    # sort and return as list of (firm, amt) tuples
    z = zip(amt_by_customer.keys(), amt_by_customer.values())
    z.sort(_tuple_cmp, reverse=True)
    return z


def lobbying_by_firm(lobbying_data):
    amt_by_firm = {}
    for transaction in lobbying_data:
        #if not transaction['registrant_is_firm']:
        #    continue
        firm = transaction['registrant_name']
        amount = transaction['amount']
        amt_by_firm[firm] = amt_by_firm.get(firm, 0) + int(float(amount))
    # sort and return as list of (firm, amt) tuples
    z = zip(amt_by_firm.keys(), amt_by_firm.values())
    z.sort(_tuple_cmp, reverse=True) # stupid in place sorting
    return z

# random util/helper functions

def slugify(string):
    ''' like the django template tag, converts to lowercase, removes
    all non-alphanumeric characters and replaces spaces with
    hyphens. '''
    return re.sub(" ", "-", re.sub("[^a-zA-Z0-9 -]+", "", string)).lower()

def amt_given_decreasing(d1, d2):
    ''' a cmp function for sort(), to sort dicts by increasing value
    of the total_given item'''

    if float(d1['total_given']) > float(d2['total_given']):
        return -1
    if float(d1['total_given']) < float(d2['total_given']):
        return 1
    else: return 0

def amt_received_decreasing(d1, d2):
    ''' a cmp function for sort(), to sort dicts by increasing value
    of the total_given item'''

    if float(d1['total_received']) > float(d2['total_received']):
        return -1
    if float(d1['total_received']) < float(d2['total_received']):
        return 1
    else: return 0

def tuple_cmp(t1, t2):
    ''' a cmp function for sort(), to sort tuples by increasing value
    of the tuple's 2nd item (index 1)'''
    if t1[1] < t2[1]:
        return -1
    if t1[1] > t2[1]:
        return 1
    else: return 0

def bar_validate(data):
    ''' take a dict formatted for submission to the barchart
     generation function, and make sure there's data worth displaying.
     if so, return the original data. if not, return false.'''

    positive_data = [d for d in data if int(float(d['value'])) > 0]
    data = positive_data
    # if all the data is 0 or if the list with only positive data is
    # empty, return false
    if sum([int(float(record['value'])) for record in data]) == 0:
        return False
    else:
        return data

def pie_validate(data):
    ''' take a dict formatted for submission to the piechart
     generation function, and make sure there's data worth displaying.
     if so, return the original data. if not, return false.'''

    positive = {}
    for k,v in data.iteritems():
        if int(float(v)) != 0:
            positive[k] = v
    if len(positive) == 0:
        return False
    else:
        return positive

def barchart_href(record, cycle, entity_type):
    if 'recipient_entity' in record.keys():
        if record['recipient_entity']:
            href = str("/%s/%s/%s?cycle=%s" % (entity_type, slugify(record['recipient_name']),
                                               record['recipient_entity'], cycle))
        else:
            href = -1

    elif 'id' in record.keys():
        if record['id']:
            href = str("/%s/%s/%s?cycle=%s" % (entity_type, slugify(record['name']),
                                               record['id'], cycle))
        else:
            href = -1
    else:
        href = -1

    return href

def generate_label(string):
    ''' truncate names longer than max_length and normalize the case
    to use title case'''
    max_length = 27
    label = string[:max_length] + (lambda x, l: (len(x)>l and "...")
                                   or "")(string, max_length)
    return label.title()


def get_metadata(entity_id, cycle, entity_type):
    ''' beginnings of some refactoring. half implemented but
    harmless. do not pet or feed.'''
    data = {}
    # check the metadata to see which of the fields are present. this
    # determines which sections to display on the entity page.
    section_indicators = {'individual': {'contributions': ('contributor_amount',),
                                         'lobbying': ('lobbying_count',)},
                          'organization' : {'contributions' : ('contributor_amount',),
                                            'lobbying': ('lobbying_count',)},
                          'politician' : {'contributions' : ('recipient_amount',)}
                          }

    entity_info = api.entity_metadata(entity_id, cycle)

    # check which types of data are available about this entity
    print 'getting metadata for %s %s' % (entity_type, entity_id)
    for data_type, indicators in section_indicators[entity_type].iteritems():
        try:
            print 'totals for %s' % indicators[0]
            print entity_info['totals'][cycle][indicators[0]]
        except: pass
        if (entity_info['totals'].get(cycle, False) and
            [True for ind in indicators if entity_info['totals'][cycle][ind] ]):
            data[data_type] = True
        else:
            data[data_type] = False

    data['available_cycles'] = entity_info['totals'].keys()
    # discard the info from cycles that are not the current one
    if entity_info['totals'].get(cycle, None):
        entity_info['totals'] = entity_info['totals'][cycle]
    data['entity_info'] = entity_info

    return data