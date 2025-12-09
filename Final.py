# --- 1. CONFIGURATION & CONSTANTS ---

# 2025 Child Tax Credit Constants
CTC_AMOUNT = 2200           # Max credit per child
CTC_REFUNDABLE_CAP = 1700   # Max refundable amount per child (ACTC)
CTC_PHASEOUT_S = 200000     # Single phase-out start
CTC_PHASEOUT_M = 400000     # Married phase-out start
CTC_PHASEOUT_H = 200000     # Head of Household phase-out start

# 2025 IRS Tax Brackets (Official)
ORDINARY_BRACKETS = {
    "s": [ # Single
        {"max": 11925,  "rate": 0.10},
        {"max": 48475,  "rate": 0.12},
        {"max": 103350, "rate": 0.22},
        {"max": 197300, "rate": 0.24},
        {"max": 250525, "rate": 0.32},
        {"max": 626350, "rate": 0.35},
        {"max": float('inf'), "rate": 0.37},
    ],
    "m": [ # Married Filing Jointly
        {"max": 23850,  "rate": 0.10},
        {"max": 96950,  "rate": 0.12},
        {"max": 206700, "rate": 0.22},
        {"max": 394600, "rate": 0.24},
        {"max": 501050, "rate": 0.32},
        {"max": 751600, "rate": 0.35},
        {"max": float('inf'), "rate": 0.37},
    ],
    "h": [ # Head of Household
        {"max": 17000,  "rate": 0.10},
        {"max": 64850,  "rate": 0.12},
        {"max": 103350, "rate": 0.22},
        {"max": 197300, "rate": 0.24},
        {"max": 250500, "rate": 0.32},
        {"max": 626350, "rate": 0.35},
        {"max": float('inf'), "rate": 0.37},
    ]
}

# Long Term Capital Gains Brackets
LTCG_BRACKETS = {
    "s": [48350, 533400],    # Single
    "m": [96700, 600050],    # Married Jointly
    "h": [64750, 566700]     # Head of Household
}

# --- 2. HELPER FUNCTIONS ---

def to_currency(amount):
    """Formats number to currency: $(1,000.00) or $1,000.00"""
    if amount < 0:
        return f"$({abs(amount):,.2f})"
    else:
        return f"${amount:,.2f}"

def calc_child_tax_credit(magi, num_children, status):
    if num_children <= 0:
        return 0 

    max_credit = num_children * CTC_AMOUNT
    threshold = CTC_PHASEOUT_M if status == "m" else CTC_PHASEOUT_S
    excess_income = max(0, magi - threshold)
    
    reduction_steps = -(-excess_income // 1000) 
    reduction_amount = reduction_steps * 50
    
    final_ctc = max(0, max_credit - reduction_amount)
    return final_ctc

def taxable_income():
    ordinary = float(Salary) + st_gain
    total_gross = ordinary + lt_gain
    return max(0, total_gross - float(Standard_deduction))

def tax_owed():
    total_taxable = taxable_income()
    
    if total_taxable <= 0:
        return {
            "ordinary": 0.0, "ltcg": 0.0, "niit": 0.0, "gross_tax": 0.0,
            "ctc_credit": 0.0, "refundable_actc": 0.0, 
            "total_liability": 0.0, "final_balance": -w_2_withholding
        }

    # Step 1: Separate Income
    gross_ordinary = float(Salary) + st_gain
    deduction = float(Standard_deduction)
    taxable_ordinary = max(0, gross_ordinary - deduction)
    taxable_ltcg = total_taxable - taxable_ordinary

    # Step 2: Ordinary Tax
    ordinary_tax = 0
    last = 0
    current_brackets = ORDINARY_BRACKETS[Marital_status]

    for b in current_brackets:
        limit = b["max"]
        if taxable_ordinary > limit:
            ordinary_tax += (limit - last) * b["rate"]
            last = limit
        else:
            ordinary_tax += (taxable_ordinary - last) * b["rate"]
            break 
            
    # Step 3: LTCG Tax
    ltcg_tax = 0
    limits = LTCG_BRACKETS[Marital_status] 
    current_stack_height = taxable_ordinary
    gains_to_tax = taxable_ltcg
    
    # 0% Bucket
    if current_stack_height < limits[0]:
        room = limits[0] - current_stack_height
        taxed_at_0 = min(gains_to_tax, room)
        gains_to_tax -= taxed_at_0
        current_stack_height += taxed_at_0

    # 15% Bucket
    if gains_to_tax > 0 and current_stack_height < limits[1]:
        room = limits[1] - current_stack_height
        taxed_at_15 = min(gains_to_tax, room)
        ltcg_tax += taxed_at_15 * 0.15
        gains_to_tax -= taxed_at_15
        current_stack_height += taxed_at_15
        
    # 20% Bucket
    if gains_to_tax > 0:
        ltcg_tax += gains_to_tax * 0.20

    # Step 4: NIIT
    niit_tax = 0
    niit_threshold = 250000 if Marital_status == 'm' else 200000
    magi = float(Salary) + st_gain + lt_gain
    
    if magi > niit_threshold:
        amount_over_threshold = magi - niit_threshold
        investment_income = lt_gain + st_gain
        niit_tax = min(amount_over_threshold, investment_income) * 0.038

    # Step 5: Credits & Withholding
    gross_tax_liability = ordinary_tax + ltcg_tax + niit_tax
    ctc_total_available = calc_child_tax_credit(magi, num_children, Marital_status)
    
    tax_after_non_refundable = max(0, gross_tax_liability - ctc_total_available)
    unused_credit = max(0, ctc_total_available - gross_tax_liability)
    
    refundable_credit = 0
    if unused_credit > 0:
        earned_income_rule = max(0, (float(Salary) - 2500) * 0.15)
        per_child_cap = num_children * CTC_REFUNDABLE_CAP
        refundable_credit = min(unused_credit, per_child_cap, earned_income_rule)
    
    total_tax_liability = tax_after_non_refundable - refundable_credit
    final_balance = total_tax_liability - w_2_withholding
    
    return {
        "ordinary": ordinary_tax,
        "ltcg": ltcg_tax,
        "niit": niit_tax,
        "gross_tax": gross_tax_liability,
        "ctc_credit": ctc_total_available,
        "refundable_actc": refundable_credit,
        "total_liability": total_tax_liability,
        "final_balance": final_balance
    }

# --- 3. MAIN PROGRAM: USER INPUTS ---

name = input("Hello, What is your name? ")
citzen = input(f"Hello {name}, are you a U.S citizen? (Enter Y or N) ")

while citzen.lower() not in ["y", "n"]:
    print("Invalid input. Please enter Y or N.")
    citzen = input(f"{name}, are you a U.S citizen? (Enter Y or N) ")

Marital_status = input(f"{name}, what is your marital status? (Enter S for single, M for married, or H for head of household): ").lower()
deductions = {
    "s": ("single", 15750),
    "m": ("married", 31500),
    "h": ("head of household", 23625)
}

while Marital_status not in deductions:
    print("Invalid input. Please enter S, M, or H.")
    Marital_status = input(f"{name}, please re-enter your marital status (S/M/H): ").lower()

if citzen.lower() == "y":
    print(f"Thank you {name}, you are eligible for standard deduction.")
    status_text, Standard_deduction = deductions[Marital_status]
    print(f"Thank you {name}, your standard deduction for {status_text} is ${Standard_deduction:,}.")
else:
    Standard_deduction = 0
    print(f"Sorry {name}, you are not qualified for standard deduction (or must itemize).")

print()
amount = input(f"{name}, do you have a salary this year? (Enter Y or N) ")
while amount.lower() not in ["y", "n"]:
    print("Invalid input. Please enter Y or N.")
    amount = input(f"{name}, do you have a salary this year? (Enter Y or N) ")

if amount.lower() == "y":
    while True:
        try:
            Salary = float(input("What is the amount of your salary this year? "))
            if Salary < 0:
                print("Invalid amount. Salary cannot be negative.")
                continue
            
            Correct_amount = input(f"You entered ${Salary:,.2f}. Is that correct? (Enter Y or N): ")
            if Correct_amount.lower() == "y":
                break
            elif Correct_amount.lower() == "n":
                continue 
            else:
                print("Invalid choice. Restarting salary entry.")
        except ValueError:
            print("Please enter numbers only.")
else:
    Salary = 0.0
    print(f"Thank you {name}, you have indicated that you do not have a salary this year.")

st_gain = 0.0
lt_gain = 0.0

has_investments = input(f"{name}, did you sell any stock or property this year? (Y/N) ")
while has_investments.lower() not in ["y", "n"]:
    print("Invalid input. Please enter Y or N.")
    has_investments = input(f"{name}, did you sell any stock or property this year? (Y/N) ")

if has_investments.lower() == "y":
    while True:
        try:
            st_input = input("Please enter your net short-term capital gains (enter 0 if none): ")
            st_gain = float(st_input)
            break 
        except ValueError:
            print("Invalid input. Please enter a numeric value.")

    while True:
        try:
            lt_input = input("Enter your Net Long-Term Capital Gains (enter 0 if none): ")
            lt_gain = float(lt_input)
            break 
        except ValueError:
            print("Invalid input. Please enter a numeric value.")

    print(f"Your Short-Term investment is: ${st_gain:.2f}")
    print(f"Your Long-Term investment  is: ${lt_gain:.2f}")

children = input(f"{name}, do you have any children? (Y/N) ").strip().lower()
while children not in ["y", "n", "yes", "no"]:
    print("Invalid input. Please enter Y or N.")
    children = input(f"{name}, do you have any children or dependents? (Y/N) ").strip().lower()

if children.startswith("y"):
    while True:
        try:
            num_children = int(input(f"{name}, how many qualifying children under age 17 do you have? "))
            if num_children < 0:
                print("Please enter a positive number.")
                continue 
            break 
        except ValueError:
            print("Invalid input. Please enter a number.")
else:
    num_children = 0
    print(f"Thank you {name}, you have indicated that you do not have any children or dependents.")

print("-" * 30)
print(f"{name}, check Box 2 of your W-2 forms and any 1099s.")
while True:
    try:
        w_2_withholding = float(input("Enter the total Federal Income Tax Withheld: "))
        if w_2_withholding < 0:
            print("Amount cannot be negative.")
            continue
        break
    except ValueError:
        print("Please enter a number.")

# --- 4. FINAL OUTPUT ---

results = tax_owed()

print("\n" + "="*40)
print(f"TAX SUMMARY FOR {name.upper()}")
print("="*40)

print(f"Ordinary Income Tax:       {to_currency(results['ordinary'])}")
print(f"Long Term Cap Gains Tax:   {to_currency(results['ltcg'])}")
print(f"Net Inv. Income Tax:       {to_currency(results['niit'])}")
print("-" * 40)
print(f"TOTAL TAX (Before Credits): {to_currency(results['gross_tax'])}")
print("-" * 40)

print(f"Child Tax Credit Applied:  {to_currency(-min(results['gross_tax'], results['ctc_credit']))}")

if results['refundable_actc'] > 0:
    print(f"Refundable Child Credit:   {to_currency(-results['refundable_actc'])}")

print("-" * 40)

print(f"Total Tax Liability:       {to_currency(results['total_liability'])}")
print(f"Less Tax Withheld:         {to_currency(-w_2_withholding)}")
print("=" * 40)

balance = results['final_balance']

if balance < 0:
    print(f"REFUND DUE TO YOU:         ${abs(balance):,.2f}")
elif balance > 0:
    print(f"AMOUNT YOU OWE:            ${balance:,.2f}")
else:
    print("Your tax balance is $0.00.")