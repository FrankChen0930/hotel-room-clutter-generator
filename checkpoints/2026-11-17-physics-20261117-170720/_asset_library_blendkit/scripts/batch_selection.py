"""Offline hotel semantic pre-screen for results returned by the official add-on."""
import re
BAD=('cartoon','stylized','fantasy','sci fi','medieval','cosplay','buckle','rack','shelf','holder','stand','trolley','checking frame','studio','display scene','booth','armour','weapon','robot','vending','life jacket','life vest','mannequin','windsock','hard hat','poker','casino','cash game','snack server','gondula','gondola','balloon','ballon','chocolate bunny','chocolate unicorn','dishwasher','dish soap','dishwashing','ammunition','rifle','pistol','cartridge','stanag')
TOKENS={
 'bag':('backpack','handbag','tote','purse','bag'),
 'luggage':('suitcase','carry on','duffel','travel bag','luggage'),
 'clothing':('jacket','coat','shirt','tshirt','jeans','trousers','pants','sock','hoodie','hat','cap'),
 'footwear':('shoe','sneaker','slipper','boot'),
 'electronics':('phone','tablet','laptop','charger','headphone','earbud','power bank'),
 'toiletry':('toothpaste','toothbrush','shampoo','soap','cream','cosmetic','lotion'),
 'towel':('towel','washcloth'),
 'paper':('paper bag','book','magazine','notebook','document'),
 'food':('snack','chips','crisps','packet','wrapper','chocolate','biscuit','candy','water bottle','juice','takeaway','takeout')}

def normalized(name):return re.sub(r'[^a-z0-9]+',' ',str(name).lower()).strip()

def has_token(name,token):
    return bool(re.search(r'(?<![a-z0-9])'+re.escape(token)+r'(?:s)?(?![a-z0-9])',name))

def semantic_rejection(name,category):
    name=normalized(name)
    if any(term in name for term in BAD):return 'HOTEL_RELEVANCE_OR_STYLE_REJECT'
    if not any(has_token(name,token) for token in TOKENS[category]):return 'SEMANTIC_NAME_MISMATCH'
    if category=='food' and has_token(name,'chips') and not any(has_token(name,t) for t in ('potato','tortilla','snack','crisps','packet','pringles','doritos','lays')):
        return 'AMBIGUOUS_CHIPS_NOT_CONFIRMED_FOOD'
    return None

def assess(meta,category,excluded=()):
    base=meta.get('assetBaseId');name=normalized(meta.get('displayName') or meta.get('name',''))
    if not base or base in excluded:return None,'ALREADY_SEEN_OR_MISSING_ID'
    if meta.get('assetType')!='model':return None,'NOT_MODEL'
    if meta.get('isFree') is not True or meta.get('canDownload') is not True:return None,'NOT_CONFIRMED_FREE_DOWNLOADABLE'
    if meta.get('license') not in {'cc_zero','royalty_free'}:return None,'UNKNOWN_LICENSE'
    reason=semantic_rejection(name,category)
    if reason:return None,reason
    size=meta.get('filesSize')
    # Installed official search.parse_result converts filesSize from bytes to KiB.
    if isinstance(size,(int,float)) and size*1024>100*1024**2:return None,'LARGE_FILE_DEFERRED'
    score=100 if meta.get('license')=='cc_zero' else 20
    if any(x in name for x in ('scan','realistic','fabric','leather')):score+=10
    return score,'SEMANTIC_CANDIDATE_NOT_VISUAL_ACCEPTANCE'

def choose(results,category,excluded=()):
    candidates=[];decisions=[]
    for index,meta in enumerate(results):
        score,reason=assess(meta,category,excluded)
        decisions.append(dict(asset_base_id=meta.get('assetBaseId'),name=meta.get('displayName') or meta.get('name'),reason=reason))
        if score is not None:candidates.append((score,-index,index))
    return (max(candidates)[2] if candidates else None),decisions
