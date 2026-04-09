from datetime import date
from models.delegation import Delegation
from models.employee import Employee

def get_active_delegates(delegator_id, module):
    """
    Returns a list of employee IDs who currently have delegated authority 
    from the delegator_id for a specific module.
    """
    today = date.today()
    # Find active delegations: Status is ACTIVE, today is between start and end date
    # Module must match or be 'All'
    delegations = Delegation.query.filter(
        Delegation.delegated_by_id == delegator_id,
        Delegation.status == 'ACTIVE',
        Delegation.start_date <= today,
        Delegation.end_date >= today,
        (Delegation.module == module) | (Delegation.module == 'All')
    ).all()
    
    return [d.delegated_to_id for d in delegations]

def is_authorized_delegate(delegator_id, acting_user_id, module):
    """
    Checks if acting_user_id is currently authorized to act for delegator_id 
    in the context of a specific module.
    """
    # If the acting user is the delegator themselves, they are always authorized
    if delegator_id == acting_user_id:
        return True
        
    today = date.today()
    delegation = Delegation.query.filter(
        Delegation.delegated_by_id == delegator_id,
        Delegation.delegated_to_id == acting_user_id,
        Delegation.status == 'ACTIVE',
        Delegation.start_date <= today,
        Delegation.end_date >= today,
        (Delegation.module == module) | (Delegation.module == 'All')
    ).first()
    
    return delegation is not None
