# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-27-10
# Implementation of the SSS (Shamir's Secret Sharing) algorithm

import random
from sslib import shamir
required_shares = 2
distributed_shares = 5
obj = shamir.to_base64(shamir.split_secret("this is my secret".encode('ascii'), required_shares, distributed_shares))
print(obj)
#pm=obj[']
data = {'required_shares': required_shares, 'prime_mod': obj['prime_mod'], 'shares': [obj['shares'][1], obj['shares'][4]]}
msg = shamir.recover_secret(shamir.from_hex(data)).decode('ascii')
print(msg)
