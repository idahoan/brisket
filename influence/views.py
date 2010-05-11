# Create your views here.

from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
import urllib, re

from influence.forms import SearchForm, ElectionCycle
from util import catcodes
import api

def brisket_context(request): 
    return RequestContext(request, {'search_form': SearchForm()})

def entity_context(request, cycle): 
    context_variables = {}    
    if request.GET.get('query', None):
        context_variables['search_form'] = SearchForm(request.GET)
    else:
        context_variables['search_form'] = SearchForm() 
    if request.GET.get('cycle', None):
        context_variables['cycle_form'] = ElectionCycle(request.GET)
    else:
        context_variables['cycle_form'] = ElectionCycle({'cycle': cycle})
    return RequestContext(request, context_variables)

def index(request):    
    return render_to_response('index.html', brisket_context(request))

def search(request):
    if not request.GET.get('query', None):
        print 'Form Error'
        HttpResponseRedirect('/')
    
    submitted_form = SearchForm(request.GET)
    if submitted_form.is_valid():        
        kwargs = {}
        query = urllib.unquote(submitted_form.cleaned_data['query'])
        cycle = request.GET.get('cycle', '2010')

        # if a user submitted the search value from the form, then
        # treat the hyphens as intentional. if it was from a url, then
        # the name has probably been slug-ized and we need to remove
        # any single occurences of hyphens. 
        if not request.GET.get('from_form', None):            
            query = query.replace('-', ' ')
        results = api.entity_search(query)

        # limit the results to only those entities with an ID. 
        entity_results = [result for result in results if result['id']]

        # if there's just one results, redirect to that entity's page
        if len(entity_results) == 1:
            result_type = entity_results[0]['type']
            name = slugify(entity_results[0]['name'])
            _id = entity_results[0]['id']
            return HttpResponseRedirect('/%s/%s/%s?cycle=%s' % (result_type, name, _id, cycle))

        if len(entity_results) == 0:
            kwargs['sorted_results'] = None
        else:
            # sort the results by type
            sorted_results = {'organization': [], 'politician': [], 'individual': []}
            for result in entity_results:
                sorted_results[result['type']].append(result)

            # keep track of how many there are of each type of result
            kwargs['num_orgs'] = len(sorted_results['organization'])
            kwargs['num_pols'] = len(sorted_results['politician'])
            kwargs['num_indivs'] = len(sorted_results['individual'])

            # organize the results for organizationa and individuals
            # into pairs to facilitate display in the template
            for k in ['organization', 'individual']:
                l = sorted_results[k]
                pairs = []
                for i in xrange(0, len(l), 2):
                    pairs.append(l[i:i+2])
                sorted_results[k] = pairs
            kwargs['query'] = query
            kwargs['cycle'] = cycle
            kwargs['sorted_results'] = sorted_results
        return render_to_response('results.html', kwargs, brisket_context(request))
    else: 
        return HttpResponseRedirect('/')

def organization_entity(request, entity_id):
    cycle = request.GET.get('cycle', '2010')
    entity_info = api.entity_metadata(entity_id, cycle)
    org_recipients = api.org_recipients(entity_id, cycle=cycle)
    recipients_barchart_data = []
    for record in org_recipients:        
        recipients_barchart_data.append({
                'key': record['name'],
                'value' : record['total_amount'],
                # currently we only display politician recipients from
                # orgs. this should be changed if we start returning
                # org-to-org data.
                'href' : str("/politician/%s/%s?cycle=%s" % (slugify(record['name']), record['id'], cycle)),
                })

    party_breakdown = api.org_party_breakdown(entity_id, cycle)
    for key, values in party_breakdown.iteritems():
        party_breakdown[key] = float(values[1])
    level_breakdown = api.org_level_breakdown(entity_id, cycle)
    for key, values in level_breakdown.iteritems():
        level_breakdown[key] = float(values[1])

    # get lobbying info
    lobbying_for_org = api.lobbying_for_org(entity_id, cycle)
    issues_lobbied_for =  [item['issue'] for item in api.issues_lobbied_for(entity_id, cycle)]
    lobbying = api.LobbyingAPI()
    lobbying_by_org = lobbying.lobbying_by_org(entity_info['name'], cycle)
    # temporary function call until this is implemented in aggregates api
    customers_lobbied_for = lobbying_by_customer(lobbying_by_org)
    return render_to_response('organization.html', 
                              {'entity_id': entity_id, 
                               'entity_info': entity_info,
                               'level_breakdown' : level_breakdown,
                               'party_breakdown' : party_breakdown,
                               'recipients_barchart_data': recipients_barchart_data,
                               'lobbying_for_org': lobbying_for_org,
                               'customers_lobbied_for': customers_lobbied_for,
                               'issues_lobbied_for': issues_lobbied_for,
                               'cycle': cycle,
                               },
                              entity_context(request, cycle))

def politician_entity(request, entity_id):
    cycle = request.GET.get('cycle', '2010')

    # metadata
    entity_info = api.entity_metadata(entity_id, cycle)
    metadata = api.politician_meta(entity_info['name'])

    top_contributors = api.pol_contributors(entity_id, cycle)

    # top sectors is already sorted
    top_sectors = api.top_sectors(entity_id, cycle=cycle)
    sectors_barchart_data = []
    for record in top_sectors:        
        try:
            sector_name = catcodes.sector[record['sector']]
        except:
            sector_name = '???'
        sectors_barchart_data.append({                
                'key': sector_name,
                'value' : record['amount'],
                'href' : str("/sector/%s/%s?cycle=%s" % (slugify(sector_name), record['sector'], cycle)),
                })

    local_breakdown = api.pol_local_breakdown(entity_id, cycle)
    for key, values in local_breakdown.iteritems():
        # values is a list of [count, amount]
        local_breakdown[key] = float(values[1])

    entity_breakdown = api.pol_contributor_type_breakdown(entity_id, cycle)
    for key, values in entity_breakdown.iteritems():
        # values is a list of [count, amount]
        entity_breakdown[key] = float(values[1])    

    # get top words spoken in congress by this legislator for this cycle
    # capitol_words = get_capitol_words(entity_info['name'], cycle, 50)

    return render_to_response('politician.html', 
                              {'entity_id': entity_id,
                               'entity_info': entity_info,
                               'top_contributors': top_contributors,
                               'local_breakdown' : local_breakdown,
                               'entity_breakdown' : entity_breakdown,
                               'metadata': metadata,
                               'sectors_barchart_data': sectors_barchart_data,
                               'cycle': cycle,
                               },
                              entity_context(request, cycle))
        
def individual_entity(request, entity_id):    
    cycle = request.GET.get('cycle', '2010')
    entity_info = api.entity_metadata(entity_id, cycle)    
    recipient_candidates = api.indiv_pol_recipients(entity_id, cycle)
    candidates_barchart_data = []
    for record in recipient_candidates:        
        candidates_barchart_data.append({
                'key': record['recipient_name'],
                'value' : record['amount'],
                'href' : str("/politician/%s/%s?cycle=%s" % (slugify(record['recipient_name']), record['recipient_entity'], cycle)),
                })

    recipient_orgs = api.indiv_org_recipients(entity_id, cycle)
    orgs_barchart_data = []
    for record in recipient_orgs:        
        orgs_barchart_data.append({
                'key': record['recipient_name'],
                'value' : record['amount'],
                'href' : str("/organization/%s/%s?cycle=%s" % (slugify(record['recipient_name']), record['recipient_entity'], cycle)),
                })

    party_breakdown = api.indiv_breakdown(entity_id, cycle)
    for key, values in party_breakdown.iteritems():
        # values is a list of [count, amount]
        party_breakdown[key] = values[1]    

    return render_to_response('individual.html', 
                              {'entity_id': entity_id,
                               'entity_info': entity_info,
                               'candidates_barchart_data': candidates_barchart_data,
                               'orgs_barchart_data': orgs_barchart_data,
                               'party_breakdown' : party_breakdown, 
                               'cycle': cycle,
                               },
                              entity_context(request, cycle))

def industry_detail(request, entity_id):
    cycle = request.GET.get("cycle", 2010)    
    entity_info = api.entity_metadata(entity_id, cycle)    
    top_industries = api.top_sectors(entity_id, cycle)

    sectors = {}
    for industry in top_industries:
        industry_id = industry['category_name']        
        results = api.contributions_by_sector(entity_id, industry_id)
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

def _tuple_cmp(t1, t2):
    ''' a cmp function for sort(), to sort tuples by increasing value
    of the tuple's 2nd item (index 1)'''
    if t1[1] < t2[1]:
        return -1
    if t1[1] > t2[1]:
        return 1
    else: return 0


def slugify(string):
    ''' like the django template tag, converts to lowercase, removes
    all non-alphanumeric characters and replaces spaces with
    hyphens. '''
    return re.sub(" ", "-", re.sub("[^a-zA-Z0-9 -]+", "", string)).lower()
