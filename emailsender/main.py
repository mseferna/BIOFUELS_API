from O365 import Account
from O365.utils.token import FileSystemTokenBackend
#tk = FileSystemTokenBackend(token_path="your token path", token_filename="filename")

credentials = ('fuelonetpro@gilbarco.com' , 'cE~lG4(u38')

account = Account(credentials,  auth_flow_type = 'public')
m = account.new_message()
m.to.add('m.seferna@gmail.com')
m.subject = 'Testing!'
m.body = "George Best quote: I've stopped drinking, but only while I'm asleep."
m.send()