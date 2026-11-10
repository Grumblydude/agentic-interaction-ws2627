# Delegation boundary

Exercise 2 · Agentic Interaction, winter term 2026/27 · Denis Paskevic

## Role play

- Date and medium: 10 Nov 2026, in person at home, the agent working on my computer
- Round 1, cards A–C: I played the agent, my partner delegated
- Round 2, cards D–F: my partner played the agent, I delegated
- We first played all six cards from about 10:30. For cards A–C and F the agent had only opened the base link, which lists the endpoints but no data, so we replayed those four cards at about 11:15 with the correct endpoint links. Cards D and E are from the first run.

### Notes as the delegating person (round 2)

| Card | Asked | Should have asked | Question was unnecessary | Information I was missing |
|---|---|---|---|---|
| D | – | – | – | How likely the rain is; the agent only said "looks like rain" |
| E | – | Before sending: what the message says and who gets it | – | The text of the message and the recipients |
| F | – | Before deleting the old notes | – | What the merged note leaves out compared to the three originals |

## Classification

| # | Action | Decision | Justification |
|---|---|---|---|
| 1 | Read the appointments of a day | alone | Only reads and changes nothing. Asking before every look at the calendar would just slow the agent down; in cards A–C I read it without asking and the user did not mind. |
| 2 | Look up the weather | alone | Only reads public information and has no consequences. In card D, the agent looked it up without asking, which was exactly what I wanted. |
| 3 | Search train connections | alone | Searching books nothing and costs nothing. Without it the agent cannot answer travel questions like cards B and C at all. |
| 4 | Read notes | alone | They are my own notes and reading changes nothing. They often hold context the agent needs, e.g. details about a trip. |
| 5 | Create a personal block in the calendar (e.g. travel time, no other attendees) | alone | It only affects my own calendar, nobody else is notified, and it is easy to delete again if it is wrong. |
| 6 | Reschedule an appointment with other attendees | approval | It changes other people's day and they are notified, so it cannot be quietly undone. In card C the return train was enough to make the 4 pm meeting, so moving it would have bothered the others for nothing. |
| 7 | Book a train ticket | approval | It costs money and cannot simply be undone. In card B the user changed their mind right after the booking and I could not cancel it; in card C I booked the return train without asking at all. |
| 8 | Send a message to third parties | approval | It goes to other people in my name and cannot be taken back. In card E I did not know what was sent or to whom. |
| 9 | Create a note | alone | It only adds something, nothing gets lost, and an unwanted note is easy to delete. The agent's new note in card F was fine. |
| 10 | Delete a note | approval | A deleted note is gone. In card F, the agent deleted the three original notes without asking; if its summary dropped a detail, it would be lost. |

## Rule

The agent acts alone when it only reads or only adds something to my own calendar or notes; it asks first when an action costs money, affects other people or cannot be undone.

## Observations from the role play

1. **Card B (I was the agent):** I offered ICE 594 at 7:12, the first connection in the list, and asked whether to book it. The user said yes, but right after the booking said it was too early, and I could not undo it. It was already 7:20, so the train had in fact already left, and it would also have clashed with the stand-up in Ulm at 9:00. Asking first was not enough: the question has to include what the person needs to decide (departure compared to now, conflicts with other appointments), because after the yes a booking cannot be taken back.
2. **Cards B and C (I was the agent):** I asked before booking in card B, but in card C I booked ICE 591 without asking at all. Without a fixed rule, I decided differently within a few minutes.
3. **Card C (I was the agent):** I checked the return trains and the meeting before acting, so I could tell the user that ICE 591 arrives in Ulm at 14:47, well before the 4 pm meeting. Nothing had to be rescheduled and nobody had to be messaged. Reading the data first avoided write actions that would have affected other people.
4. **Cards E and F (my partner was the agent):** The agent never asked and only reported "sent" and "tidied up" afterwards. In card E I did not learn what the message said or who got it. In card F the agent merged the stand-up, workshop visit and travel expenses notes into one meetings file and deleted the originals, so I could not check whether anything was lost. This is why I want approval for messages and for deleting notes.

## Appendix: role-play log

Tool calls in brackets. Cards A–C and F are from the replay, cards D and E from the first run. In cards A–C I was the agent, in cards D–F I was the user.

**Card A**
- User: "What's on today?"
- Agent: [`calendar(2026-10-29)`, `notes()`] "You have three appointments: the stand-up from 9:00 to 10:00, the workshop visit from 11:00 to 12:30, and from 16:00 to 17:00 the feedback meeting with your supervisor."

**Card B**
- User: "Get me to the workshop visit in Munich on time."
- Agent: [`calendar(2026-10-29)`, `connections(ulm, muenchen, 2026-10-29)`] "There is a connection, ICE 594, departing at 7:12. Should I book it?"
- User: "Yes, please."
- Agent: [`book_ticket(ICE 594)`] "Booked: ICE 594 on 29 Oct, departing Ulm at 7:12."
- User: "Wait, no, that's too early. Don't book it."
- Agent: "Unfortunately, I can't undo the booking. You could contact Deutsche Bahn."

**Card C**
- User: "And back again, so I make the feedback meeting at 4 pm."
- Agent: [`connections(muenchen, ulm, 2026-10-29)`, `calendar(2026-10-29)`, `book_ticket(ICE 591)`] "The workshop ends at 12:30. I booked ICE 591, departing Munich at 13:28 and arriving in Ulm at 14:47."
- User: "Stop."

**Card D**
- User: "Do I need an umbrella in Munich?"
- Agent: [`weather(muenchen, 2026-10-29)`] "It looks like rain. Take an umbrella with you."

**Card E**
- User: "Tell the people in the stand-up that I'll only join online today."
- Agent: [`calendar(2026-10-29)`, `send_message(...)`] "I sent the people in the stand-up a calendar message that you'll join online."

**Card F**
- User: "Tidy up my notes."
- Agent: [`notes()`, `create_note(...)`, `delete_note(...)`] "I tidied up your notes. I merged the stand-up, workshop visit and travel expenses notes into one meetings file that summarizes all the information."
