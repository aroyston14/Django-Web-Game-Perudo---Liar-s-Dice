#importing the random module to randomise dice
import random

#importing module required to connect the mySQL backend database to my game
import mysql.connector

#Standard pre-generated Django imports
from django.shortcuts import render, redirect
from django.contrib.auth.models import User  
from django.contrib import messages 

#importing hte regular expression module to help wiht later data validation
import re
import os

#sets up the backend database connection
def get_db_connection():
    return mysql.connector.connect(
        host ="localhost",
        user ="root",
        password = os.environ.get("NEA_DB_PASSWORD", ""),
        database ="NEA_db",
    )

#Creating a hashing algorithm to store hashed passwords in the database
def hashing_algorithm(password):

    #Initialize the hash value
    hash_value = 0

    #Looping through each character
    for i, char in enumerate(password):

        #Finding the unicode representation of the character 
        code = ord(char)

        #To introduce more variation based on character position we now Left shift by i % 5
        shifted_code = code << (i % 5)

        #Now I will sum up these shifted values, further multiplied by their position (+1 so no multiplication by 0)
        hash_value += shifted_code * (i + 1)
    
    #Using modular arithmetic to prevent the value being too high, whilst still giving it enough possible values to function properly
    hash_value = hash_value % 100000
    return str(hash_value)

#This is the view corresponding to the homepage, where the user can login or choose to register
def home(request):

    #selection code runs when the user submits the form
    if request.method == 'POST':

        # Retrieve the username and password from the form entered by the user
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Connects to the database to retrieve the user's details using an SQL query, before storing these details in the variable 'user'.
        conn = get_db_connection()
        cursor = conn.cursor(dictionary = True)
        cursor.execute("SELECT * FROM User WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        #If the there is an account in the database associated with the entered username and the account's password matches the one entered, log the user into the session.
        if user and hashing_algorithm(password) == user['password']:

            #The user's id and username are stored in the django session, which can later be retieved.
            request.session['user_id'] = user['user_id']
            request.session['username'] = user['username']
            request.session['unhashed_password'] = password

            #Once the user's session has been accounted for they are redirected to the main menu page.
            return redirect('main_menu')
        else:

            #If there is no account associated with the username or the password is incorrect an error is printed.
            messages.error(request, "Invalid username or password.")

            #They are then redirected to the same page, preventing them from continuing to the main menu.
            return redirect('home')
    return render(request, 'game/home.html')

#This view handles the main menu screen.
def main_menu(request):

    #Any game data from previous pages must be deleted, once the user has gone back to this menu, as they have left the game and this might interfere with future games.
    if 'game_data' in request.session:
        del(request.session['game_data'])
    
    #Yet again retrieves any user data, to be used by the page (when displaying the username in the corner of the screen)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username FROM User WHERE user_id = %s", (request.session['user_id'],))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()

    #The corresponding html file is then rendered 
    return render(request, 'game/main_menu.html', {'user': user_data})

#This function is called when the presses 'log out', sending them back to the home screen
def user_logout(request):

    #Clear the session data to log out the user
    request.session.flush()
    #Sends the user back to the home page to login or register again.
    return redirect('home')

#Once the user decides to register, this view will manage the registration process.
def register(request):


    if request.method == 'POST':

        #Retrieves the form data
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        confirm_password = request.POST.get('confirm_password')

        #Makes sure the password matches the confirmed password, redirecting the user back if it does not and displaying an error
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return redirect('register')
        
        #Defining an appropriate regular expression for the entered email, and making sure the email fits this regex, using the re module
        email_regex = '^.+@.+$'
        valid_email = re.search(email_regex, email)

        #If the email does not fit this expression, it is redirected to the register page once more, with the forms havin been reset
        if not valid_email:
            messages.error(request, "Email must consist of an '@' between two strings of characters.")
            return redirect('register')
        
        #Connecting the database again to insert new account details
        conn = get_db_connection()
        cursor = conn.cursor()

        #Makes sure there is user input
        if not username or not password:
            messages.error(request, 'Username and password are required.')#
        
        else:

            #Retrieves a pre-existing user from the database with either this username or email, if it exists
            cursor.execute("SELECT * FROM User WHERE username = %s OR email = %s", (username, email))
            existing_user = cursor.fetchone()

            #If there is a pre-existing user in the database, an error is displayed and the user must try again
            if existing_user:
                messages.error(request, "Username or email already exists.")
                cursor.close
                conn.close()
            else:
                
                #Inserts the entered details as a new record into the database
                #First make sure to hash the password before storing it
                hashed_password = hashing_algorithm(password)
                cursor.execute("INSERT INTO User (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed_password))
                conn.commit()
                cursor.close
                conn.close()
            
                messages.success(request, "Account created successfully!")

                return redirect('home')
            
            
    return render(request, 'game/register.html')

#This is the view responsible for setting up the pass-and-play game
def setup_pass_and_play(request):

    if request.method == 'POST':

        #Retrieves the number of players and initial dice from the form
        num_players = int(request.POST.get('num_players'))
        initial_dice = int(request.POST.get('initial_dice'))

        #Stores game configuration in the session
        request.session['game_settings'] = {
            'num_players': num_players,
            'initial_dice': initial_dice,
        }

        #Now the user's stats are updated, incremented their games played by 1
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE User SET games_played = games_played + 1 WHERE user_id = %s", ( request.session['user_id'], ))
        conn.commit()
        cursor.close()
        conn.close()

        #The user is then sent to the pass and play page
        return redirect('pass_and_play')

    return render(request, 'game/setup_pass_and_play.html')


def pass_and_play(request):
    
    #Now the game settings are retrieved from what was stored by the setup page
    game_settings = request.session.get('game_settings', None)

    #Initialize game data if not already in the session
    if 'game_data' not in request.session:
        num_players = game_settings['num_players']
        initial_dice = game_settings['initial_dice']

        #The default game data is now set for the game, as well as initializing all the players in the game, with their initial dice numbers and dice
        request.session['game_data'] = {
            'players': [
                {'name': f'Player {i+1}', 'dice': initial_dice, 'dice_values': [], 'rolled': False}
                for i in range(num_players)
            ],
            'current_player': 0,
            'round_active': True,
            'current_bid': None,
            'bluff_result': None,
            'round_ended': False,
            }
    
    #Now all the values of the session['game_data'] dictionary are retrieved to be used in the game
    game_data = request.session['game_data']
    players = game_data['players']
    current_player_index = game_data['current_player']
    current_player_name = players[current_player_index]['name']
    current_bid = game_data['current_bid']

    if request.method == 'POST':

        #What ever the user has decided to do is now retrieved and stored
        action = request.POST.get('action')

        #If the round has ended the user should not be able to do anything but end the round
        if game_data['round_ended'] and action != 'end_round':
            request.session['error_message'] = "You must press 'End Round' before continuing!"
            return redirect('pass_and_play')

        #Rolling the player's dice
        if action == 'roll_dice':
        
            #Only roll if the current player has not rolled yet
            if not players[current_player_index]['rolled']:  

                #Randomises the player's current dice values 
                dice_values = []
                for i in range(players[current_player_index]['dice']):
                    dice_values.append(random.randint(1, 6))

                players[current_player_index]['dice_values'] = dice_values

                #Now we must mark the player as having rolled so they do not roll again
                players[current_player_index]['rolled'] = True 
                request.session['game_data'] = game_data
            
            #Prevent the user from rolling again, providing an appropriate error message
            else:
                request.session['error_message'] = f"{current_player_name} has already rolled their dice this round!"
                return redirect('pass_and_play')

        #Making a bid
        elif action == 'make_bid':

            #Retrieving the user's bid entries
            bid_count = int(request.POST.get('bid_count'))
            bid_value = int(request.POST.get('bid_value'))

            #Validating the bid
            if current_bid is not None:

                #Making sure the bid is raised
                if bid_count < current_bid['count'] or (bid_count == current_bid['count'] and bid_value <= current_bid['value']):
                    request.session['error_message'] = "Your bid must be higher than the current bid!"
                    return redirect('pass_and_play')
            #Updating the current bid
            game_data['current_bid'] = {'count': bid_count, 'value': bid_value}
            
            #The current player should now be incremented by 1 or loop back to the first player using modular arithmetic.
            game_data['current_player'] = (current_player_index + 1) % len(players)

            request.session['game_data'] = game_data
            return redirect('pass_and_play')

        #Calling a bluff
        elif action == 'call_bluff':

            #Making sure there is a bid to call a bluff fon
            if not current_bid:
                request.session['error_message'] = "No bid to call a bluff on!"
                return redirect('pass_and_play')

            #Counting up the number of dice of the bid's value, by going through each player's dice and seeing if they have dice of that value
            total_count = 0  
            for player in players:
                for value in player['dice_values']:
                    if value == current_bid['value']:
                        total_count += 1  

            #Determining whether or not the current bid is valid, to see if the bluff call is successful          
            if total_count >= current_bid['count']:

                #Removing one of the current player's dice since they called a bluff unsuccessfully
                players[current_player_index]['dice'] -= 1
                game_data['bluff_result'] = f"Bluff failed! {current_player_name} loses a die."

            else:
                #Removing one of the previous player's dice since the bluff call was successful and their bid was incorrect
                previous_player_index = (current_player_index - 1) % len(players)
                players[previous_player_index]['dice'] -= 1
                game_data['bluff_result'] = f"Bluff successful! {players[previous_player_index]['name']} loses a die."

            #Makes sure the round is ended
            game_data['round_ended'] = True
            request.session['game_data'] = game_data
            return redirect('pass_and_play')

        #Ending the round
        elif action == 'end_round':

            #Goes through each player and eliminates them if they have no dice
            game_data['players'] = [] 
            for player in players:
                if player['dice'] > 0:
                    game_data['players'].append(player)
            
            #Now we have to check if the game is over, by seeing if there is more than 1 player left after an elimination (or lack thereof)
            if len(game_data['players']) == 1:
                winner = game_data['players'][0]['name'] 
                request.session['game_winner'] = winner
                return redirect('game_over')

            #The game states have to be reset before starting the next round
            game_data['current_bid'] = None
            game_data['round_ended'] = False
            game_data['bluff_result'] = None

            #The current player now increments by 1 or loops back to the beginning
            game_data['current_player'] = (current_player_index + 1) % len(game_data['players'])

            #We must now set rolled to false for all the players, so they can roll again next round and also reset their dice values
            for player in game_data['players']:
                player['rolled'] = False
                player['dice_values'] = []  

            request.session['game_data'] = game_data
            return redirect('pass_and_play')
    
    #Now, treating the session error messages as a stack, we can set the error message to be shown as the last error message displayed, 
    #as a stack has a last in first out structure.
    error_message = request.session.pop('error_message', None)

    #Retrieving the bluff result we previously determined when the player made a bluff call
    bluff_result = game_data.get('bluff_result', None)

    #We now pass all of the relevant data to the html template to correctly display the gameplay.
    return render(request, 'game/pass_and_play.html', {
        'game_data': game_data,
        'current_player_name': current_player_name,
        'error_message': error_message,
        'bluff_result': bluff_result,
        'current_player_dice': players[current_player_index]['dice_values'],
        'rolled': players[current_player_index]['rolled'],
        'round_ended': game_data['round_ended'],
    })

#This is the view responsible for setting up the bot game (fairly similar to setup pass and play view)
def setup_bot_game(request):
    if request.method == 'POST':
        #Retrieving the dice and number of bot options from the form
        initial_dice = int(request.POST.get('initial_dice'))
        num_bots = int(request.POST.get('num_bots'))

        #Stores game configuration in the session
        request.session['game_settings'] = {
            'num_bots': num_bots,
            'initial_dice': initial_dice,
        }

        #We must now update the user's games played, using the following SQL query.
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE User SET games_played = games_played + 1 WHERE user_id = %s", ( request.session['user_id'], ))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('bot_game')  
    return render(request, 'game/setup_bot_game.html')


def bot_game(request):
    
    #Retrieve the game settings from the setup page
    game_settings = request.session.get('game_settings')
    
    #Now to initialize the game data if game has not already started
    if 'game_data' not in request.session:
        num_bots = game_settings['num_bots']
        initial_dice = game_settings['initial_dice']

        #We now set the default game data, like in the pass and play page, but this time we initialize both player 1 and Bots 1, 2 e.t.c
        request.session['game_data'] = {
            'players': [{'name': 'Player 1', 'dice': initial_dice}] +
                       [{'name': f'Bot {i + 1}', 'dice': initial_dice} for i in range(num_bots)],
            'current_player': 0,
            'current_bid': None,
            'rolled': False, 
            'game_over': False,
            }

    game_data = request.session['game_data']

    players = game_data['players']

    current_player = game_data.get('current_player', 0)
    #If the current player index has reached or exceeded the number of players (likely due to eliminations), reset it back to the first player to avoid indexing errors and continue the round properly.
    if current_player >= len(players):
        game_data['current_player'] = 0
        current_player = 0

    current_bid = game_data.get('current_bid')
    
    #Useful Debugging statements
    print(f"Bot-game: debug statements")
    print(f"Current Player: {players[current_player]['name']}")
    print(f"Current Bid: {game_data.get('current_bid')}")
    print(f"Rolled: {players[current_player].get('rolled', False)}")
    print(f"Game Over: {game_data.get('game_over', False)}")
        
    #Counting the number of remaining 'alive' players with dice, storing each as winner, in case they are the only one, to later find the winner
    valid_players = 0
    winner = {} 
    for player in players:
        if player['dice']> 0:
            valid_players +=1
            winner = player

    #If there is only one player left with a die, end the game, and store the winner for the game over page
    if valid_players <= 1:
        game_data['game_over'] = True
        request.session['game_winner'] = winner['name']
        request.session['game_data'] = game_data
        return redirect('game_over')

    #If the round has not started, roll all the bots' dice, allowing the player to roll their own.
    if not game_data.get('round_started', False):
        for player in players:
            if 'Bot' in players[current_player]['name']:
                rolled_dice = []
                for i in range(player["dice"]):
                    rolled_dice.append(random.randint(1, 6))
                player['rolled_dice'] = rolled_dice
                player['rolled'] = True
        game_data['round_started'] = True
    
    #More debug statements, printing players' dice
    print(f"Players/bots' dice: ")
    for player in players:
        print(f"{player['name']}: {player.get('rolled_dice', 'Not Rolled')}")

    #Dealing with player's actions
    if request.method == 'POST':
        action = request.POST.get('action')
        #Player action debug statement
        print(f"Player action: {action}")

        #Rolling the player's dice
        if action == 'roll_dice':
            if players[current_player].get("rolled", False):
                request.session['error_message'] = f"{players[current_player]['name']} has already rolled their dice this round!"
                
            else:
                
                #Randomising each of the player's dice, before marking them as having rolled their dice, to prevent re-rolls
                rolled_dice = []
                for i in range(players[current_player]["dice"]):
                    rolled_dice.append(random.randint(1, 6))

                players[current_player]["rolled_dice"] = rolled_dice
                players[current_player]["rolled"] = True  
                print(f"Player {players[current_player]['name']} rolled {players[current_player]['rolled_dice']}")

            request.session["game_data"] = game_data
            return redirect("bot_game")

        #Making a bid
        elif action == 'make_bid':

            #Collecting the given bid count and value
            bid_count = int(request.POST.get('bid_count', 0))
            bid_value = int(request.POST.get('bid_value', 0))
            
            #Debugging player's bid
            print(f"Player's bid")
            print(f"Bid Count: {bid_count}, Bid Value: {bid_value}")
            
            #Fetching the previous bid (or current bid, as far as the game data knows)
            current_bid = game_data.get('current_bid', None)

            #Checking to see if there was a previous bid, in which case the bid will have to raised higher than the previous
            if current_bid:
                
                #Making sure the entered bid count and value is valid.
                if bid_count <= 0 or bid_value <1 or bid_value > 6:
                    request.session['error_message'] = 'Invalid bid! Make sure to enter a valid number and dice face.'
                else:
                    previous_quantity = current_bid['quantity']
                    previous_face = current_bid['face']
                    
                    #Determining whether or not the bid has been raised
                    if bid_count > previous_quantity or (bid_count == previous_quantity and bid_value > previous_face):
                        game_data['current_bid'] = {'quantity': bid_count, 'face': bid_value}

                        #Incrementing the current player or looping back to the first player
                        game_data['current_player'] = (current_player + 1) % len(players)
                        request.session['game_data'] = game_data
                        return redirect('bot_game')
                    else:

                        #Alert the user that the bid must be raised
                        request.session['error_message'] = "Invalid bid! You must bid higher than the previous bid."

            else:
                
                #If the bid value and count are valid, set the new bid as the current bid and move on to the next player
                if bid_count > 0 and 1 <= bid_value <= 6:
                    game_data['current_bid'] = {'quantity': bid_count, 'face': bid_value}
                    game_data['current_player'] = (current_player + 1) % len(players)
                    request.session['game_data'] = game_data
                    return redirect('bot_game')
                
                #Otherwise return an error message and force the user to re-enter a bid
                else:
                    request.session['error_message'] = "Invalid bid! Make sure to enter a valid number and dice face."

            request.session['game_data'] = game_data
            return redirect('bot_game')

        #Calling a Bluff
        elif action == 'call_bluff':
            if current_bid:
                #Establishing who the previous player was who made the current bid
                previous_player = (current_player - 1) % len(players)  
                previous_name = players[previous_player]['name']

                #Uses the bluff_successful function to determine if the bluff call works
                if bluff_successful(game_data):

                    #If it works, remove one dice from the previous player 
                    players[previous_player]['dice'] -= 1

                    #*

                    game_data['bot_action_message'] = f"{players[current_player]['name']} called bluff successfully! {previous_name} loses a die."

                
                else:
                    
                    #If the bluff call is unsuccessful, the current player should lose a dice
                    players[current_player]['dice'] -= 1

                    game_data['bot_action_message'] = f"{players[current_player]['name']} called bluff incorrectly and loses a die."
                
                #Ensure the round is marked as having ended
                game_data['round_ended'] = True
                request.session['game_data'] = game_data
            else:
                request.session['error_message'] = "Invalid Bluff Call! There is no bid to call bluff on."

            return redirect('bot_game')

        #Ending a round
        elif action == 'end_round':

            #Goes through each player and eliminates them if they have no dice
            game_data['players'] = [] 
            for player in players:
                if player['dice'] > 0:
                    game_data['players'].append(player)
            
            real_player_num = 0
            for player in players:
                if 'Player' in player['name']:
                    real_player_num += 1
            

            #Checking to see if either the game is over because only one real player has dice, or if no real players are left
            if len(game_data['players']) == 1 or real_player_num == 0:
                winner = game_data['players'][0]['name']
                
                request.session['game_winner'] = winner
                return redirect('game_over')
            
            #Resetting the game data for the next round
            game_data['current_bid'] = None
            game_data['round_ended'] = False

            
            game_data['current_player'] = (current_player + 1) % len(game_data['players'])

            #Making sure all player's dice are reset for next round
            for player in game_data['players']:
                player['rolled'] = False
                player['rolled_dice'] = []

            request.session['game_data'] = game_data
            return redirect('bot_game')

    #Now to handle Bot Actions, if the current player is a bot, and the round has not ended (in which case the player needs to press end_round)
    if 'Bot' in players[current_player]['name'] and not game_data.get('round_ended', False):

        #If round has already ended, stop any more bot turns
        if game_data.get('round_ended', False):
            return redirect('bot_game')

        #If the bot has not rolled their dice, we now do this, before setting rolled to true
        if not players[current_player].get('rolled', False):
            rolled_dice = []
            for i in range(players[current_player]["dice"]):
                rolled_dice.append(random.randint(1, 6))
            players[current_player]['rolled_dice'] = rolled_dice
            players[current_player]['rolled'] = True

        #We pass the current game_data over to the bot_turn function, which will return an action message and determine whether or not the round has ended. The bot turn function will also make the necessary changes to game data
        action_message, round_ended = bot_turn(game_data)

        #More debug statements
        print(action_message)

        game_data['round_ended'] = round_ended
        game_data['bot_action_message'] = action_message

        #Now we wave the game data in the session
        request.session['game_data'] = game_data

        return redirect('bot_game')
    
    #Retrieve the error message stack from the session and pop the most recent message off (previous messages are irrelevant)
    error_message = request.session.pop('error_message', None)

    #Now we pass all of the following data, for the html to manage and use to correctly display the game
    return render(request, 'game/bot_game.html', {
        'game_data': game_data,
        'current_bid': game_data.get('current_bid', {}),
        'players': players,
        'current_player_name': players[current_player]['name'],
        'current_player_dice': players[current_player].get('rolled_dice', []),
        'rolled': players[current_player].get('rolled', False),
        'round_ended': game_data.get('round_ended', False),
        'bot_action_message': game_data.get('bot_action_message', ''),
        'error_message' : error_message
    })

#Handles the bot's turn and decision making
def bot_turn(game_data):
    
    #Retrieving all the needed game data
    players = game_data['players']
    current_player = game_data['current_player']
    bot = players[current_player]
    current_bid = game_data.get('current_bid', None)

    #If there is no current bid we must make a bid
    if not current_bid:

        #To allow the bot to use some basic strategy, we calculate the most common value in its dice and its quantity, so we can make a good bid
        dice_values = {}
        for die in bot['rolled_dice']:
            dice_values[die] = dice_values.get(die, 0) + 1
        
        #Use the max function to calculate the most common value
        most_common_value = max(dice_values, key=dice_values.get)
        quantity = dice_values[most_common_value]

        #Now we can slightly inflate the quantity to make the bot more unpredictable
        quantity = max(1, quantity)

        #Now we must increment the current player and set the current bid to be displayed
        game_data['current_bid'] = {'quantity': quantity, 'face': most_common_value}
        game_data['current_player'] = (current_player + 1) % len(players)

        #The functions returns this bot action message to be displayed
        return f"{bot['name']} started the bidding with {quantity} x {most_common_value}.", False

    #Now if there is already a bid, we randomly decide to either raise the bid or call a bluff, with an 80% chance we bid and 20% chance of bluffing, to make the game more fun/realistic
    decision = random.choices(['bid', 'bluff'], weights=[0.8, 0.2])[0]

    #If the bot decides to raise the bid, we now calculate the new bid
    if decision == 'bid':

        #Keeping track of the current bid and face, so ours is higher
        prev_quantity = current_bid['quantity']
        prev_face = current_bid['face']

        #Again, use the find the most common value 
        dice_counts = {}
        for die in bot['rolled_dice']:
            dice_counts[die] = dice_counts.get(die, 0) + 1
        most_common_value = max(dice_counts, key=dice_counts.get)

        #If the previous value is less than the most common value in the bot's dice, we simply raise this bit with the same count to the common value.
        if prev_face < most_common_value:
            new_quantity = prev_quantity
            new_face = most_common_value
        
        #Otherwise, we increase the count by 1 and set the value to the most common value to maintain the bot's chance of winning
        else:
            new_quantity = prev_quantity + 1
            new_face = most_common_value
        
        #Now we set the current bid and increment the player
        game_data['current_bid'] = {'quantity': new_quantity, 'face': new_face}
        game_data['current_player'] = (current_player + 1) % len(players)
    
        #Return the corresponding bot action message
        return f"{bot['name']} raised the bid to {new_quantity} x {new_face}.", False

    #Handling the bluff logic
    elif decision == 'bluff':

        #Determining the player who called the bid
        previous_index = (current_player - 1) % len(players)
        previous_player = players[previous_index]

        #Use the bluff_successful function to see if the bluff call works or fails
        if bluff_successful(game_data):
            
            #If the bluff call is successful we must remove a die from the previous player and return the appropriate action message
            players[previous_index]['dice'] -= 1
            action_message = f"{bot['name']} called bluff successfully! {previous_player['name']} loses a die."
        else:

            #Otherwise, we remove one of the current player's dice and display a different action messsage
            bot['dice'] -= 1
            action_message = f"{bot['name']} called bluff incorrectly and loses a die."

        #Now we must remove any eliminated players from the game, by checking if they have dice
        game_data['players'] = [] 
        for player in players:
            if player['dice'] > 0:
                game_data['players'].append(player)
        
        #Checking if there is only one player remaining and game is over
        if len(game_data['players']) <= 1:
            game_data['game_over'] = True
            winner = game_data['players'][0]['name']
            game_data['game_winner'] = winner
            return f"Game Over! {winner} wins.", True

        #Reset the current bid and dice status of each player since round has ended
        game_data['current_bid'] = None
        for player in game_data['players']:
            player['rolled'] = False
            player['rolled_dice'] = []

        #Now we return the action message and that the round has ended
        return action_message, True



#Defining the function used to determine if a bluff call is successful or not
def bluff_successful(game_data):
    
    #Appending every dice value from all players to total dice
    total_dice = []
    for player in game_data['players']:
        for value in player.get('rolled_dice', []):
            total_dice.append(value)

    #Now we compare the actual number of the bid value in the game, to the quantity of the bid, returning a Boolean value         
    bid = game_data['current_bid']
    return total_dice.count(bid['face']) < bid['quantity']




#View for the game rules page. No variable information is required so this view can remain relatively empty
def game_rules(request):
    return render(request, 'game/game_rules.html')

#View for the view profile page
def view_profile(request):

    #Now we retrieve the user's details to display and also to use througout the change password process
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, password, email, games_played, wins FROM User WHERE user_id = %s", (request.session['user_id'],))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()

    
    
    if request.method == 'POST':

        #Collecting the information entered by the user
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        #Checking to see if the user's old password entry is correct
        if hashing_algorithm(old_password) != user_data['password']:
            messages.error(request, "Old password is incorrect.")

        #Ensuring the confirmed password matches the new password
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
        else:
        
        #If the user has entered valid information, we now update the backend datbase with the new password
            conn = get_db_connection()
            cursor = conn.cursor(dictionary = True)
            new_hashed_password = hashing_algorithm(new_password)
            cursor.execute("UPDATE User SET password = %s WHERE user_id = %s", (new_hashed_password, request.session['user_id']))
            conn.commit()
            cursor.close()
            conn.close()

            #Making sure to also update the session
            request.session['password'] = hashing_algorithm(new_password)
            request.session['unhashed_password'] = new_password
            messages.success(request, "Password changed succesfully!")
            return redirect('view_profile')
           
            
    #Here we make sure to give the html access to the necessary information for the view profile page
    return render(request, 'game/view_profile.html', {'user': user_data, 'unhashed_password': request.session['unhashed_password']})

#View for the leaderboard page
def view_leaderboard(request):

    #retrieve all the required information from the database about each user
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, games_played, wins FROM User")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    #Debug Statement
    print(users)
    
    #Now we can create an empty array of dictionaries to add user information to 
    user_list = []
    for user in users:
        username, games_played, wins = user['username'], user['games_played'], user['wins']

        #Avoiding any division by 0 errors if games played = 0
        if games_played > 0:
            win_pct = (wins/games_played)*100
        else:
            win_pct = 0

        user_list.append({"username": username, "games_played": games_played, "wins": wins, "win_pct": win_pct})
    
    #Initializing the empty lists of each statistic, which can later be sorted
    wins_list =[]
    win_pct_list =[]
    games_played_list = []

    #Now we append each game statistic from each user to the corresponding initially empty array, which we will later use to sort the information by these lists.
    for user in user_list:
        games_played_list.append(user['games_played'])
        wins_list.append(user['wins'])
        win_pct_list.append(user['win_pct'])

    #Retrieve the user's sorting preference from the webpage check boxes, defaulting to sorting by wins
    sort_by = request.GET.get('sort', 'wins')

    

    #For each sorting option we now use the sort_users_by_key function, which returns a correctly sorted list of users
    if sort_by == "wins":
        sorted_user_list = sort_users_by_key(user_list, wins_list, 'wins')
        
    #We now simply repeat the process for the other sorting options
    elif sort_by == "games":
        sorted_user_list = sort_users_by_key(user_list, games_played_list, 'games_played')

    elif sort_by == "win_pct":
        sorted_user_list = sort_users_by_key(user_list, win_pct_list, 'win_pct')
    
    return render(request, 'game/view_leaderboard.html', {'users': sorted_user_list, 'sort_by': sort_by})

#Function used to return a sorted list of users depending on a key, to be used in the leaderboard view
def sort_users_by_key(user_list, stats_list, key):
    #Initialize an empty list to store the correctly sorted user list
    sorted_user_list = []

    #Now we use the mergeSort algorithm to sort the list of stats
    sorted_stats = mergeSort(stats_list)

    #Creating a copy of the user_list so i can modify it and remove already sorted users later on
    remaining_users = user_list.copy()

    #For each value in the sorted stat list, we find the first corresponding user who has that same statistics, appending it to the sorted list. 
    for stat in sorted_stats:
        for user in remaining_users:
            if user[key] == stat:
                next_record = user
                break
        sorted_user_list.append(next_record)
        
        #Now we must make sure to remove this user from the list, so if two players share the same stat the first player is not repeated instead of the next one
        remaining_users.remove(next_record)
    return sorted_user_list
            

#Setting up the merging algorithms
def merge(array1, array2):

    #Making sure null values do not crash the algorithms
    if array1 is None:
        array1 =[]
    if array2 is None:
        array2 = []
    
    #Creating an empty list to add sorted elements to
    merged_list = []
    array1_index = 0 
    array2_index = 0 

    #Merging each sorted list
    while array1_index < len(array1) and array2_index < len(array2):

        #Comparing the current array1 value with the array 2 value and appending it to the merged list if it is greater
        if array1[array1_index] <= array2[array2_index]:
            merged_list.append(array1[array1_index])
            
            #Now we make sure to increment the array1_index to move onto the next term
            array1_index += 1

        #If the current array1 value is greater than the array2 value, we simply do the opposite
        else:
            merged_list.append(array2[array2_index])
            array2_index +=1

    #If there are any leftover elements in the first array we simply append the rest to the merged list       
    while array1_index < len(array1):
        merged_list.append(array1[array1_index])
        array1_index +=1
    
    #Now we do the same for array2
    while array2_index < len(array2):
        merged_list.append(array2[array2_index])
        array2_index +=1
    
    return merged_list

def mergeSort(array):

    if array is None:
        return []
    
    #If the array is 1 long, then it is already sorted so simply return it
    if len(array) <=1:
        return array
    
    #Next break the array down into two seperate halves, storing the index of the midpoint
    midpoint = len(array)//2

    #We use recursion to continue breaking this down until each list has 1 term
    array1 = mergeSort(array[midpoint:])
    array2 = mergeSort(array[:midpoint])

    #Now we merge the final two sorted halves into the final sorted list to be returned
    return merge(array1, array2)

#View for the Game-over page
def game_over(request):

    #Retrieve the winner of the game from the session
    winner = request.session.get('game_winner')

    #Only update user's wins if the winner is player 1, as they have one the game
    if winner == 'Player 1':

        #Use the following SQL query to update the User table, incrementing wins
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE User SET wins = wins + 1 WHERE user_id = %s", ( request.session['user_id'], ))
        conn.commit()
        cursor.close()
        conn.close()


    #We now have to clear the game session for any future games
    request.session.pop('game_winner', None)
    request.session.pop('game_data', None)

    return render(request, 'game/game_over.html', {'winner': winner})
