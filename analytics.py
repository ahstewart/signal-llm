import plotly.express as px
import chart_studio.plotly as py
from plotly.subplots import make_subplots
import sqlite3 as sql
import os
import pandas as pd
from dash import Dash, dcc, html, callback, Output, Input, dash_table
import io

app = Dash(__name__)

cwd = os.getcwd()

con = sql.connect(f'{cwd}\\data\\plaintext.db')
cursor = con.cursor()

messages_clean_query = "select u.rowid, u.type, u.sent_at, DATETIME(ROUND(u.sent_at/1000), 'unixepoch', 'localtime') as date_sent, u.body, u.hasAttachments, u.hasFileAttachments, u.hasVisualMediaAttachments, " \
                       "u.sourceDevice, c.name, c.profileName, c.profileFamilyName, c.profileFullName from messages u INNER JOIN conversations c " \
                       "on u.sourceServiceId = c.serviceId where u.conversationId = '7666311e-a841-4ee2-b0cb-ac92463eb0d5' " \
                       "and u.body not like '🤖%' and u.body not like 'Nick AI:%'"
reactions_clean_query = "select r.emoji, r.messageReceivedAt, r.targetTimestamp, r.emoji_sender, r.emoji_receiver, m.body from " \
                        "(select r.*, c.profileFullName as emoji_receiver from (select r.emoji, r.messageId, r.messageReceivedAt, " \
                        "r.targetAuthorAci, r.targetTimestamp, c.profileFullName as emoji_sender from reactions r INNER JOIN conversations c " \
                        "on r.fromId = c.id where r.conversationId='7666311e-a841-4ee2-b0cb-ac92463eb0d5') r INNER JOIN conversations c " \
                        "on r.targetAuthorAci = c.serviceId) r INNER JOIN messages m on r.messageId = m.id"
total_counts_query = f"select profileFullName, count(*) as num_messages from ({messages_clean_query}) group by profileFullName order by num_messages desc"
reaction_summary_query = f"select emoji_sender, count(distinct emoji) as variety, count(*) as frequency, emoji as fav_emoji from " \
                         f"({reactions_clean_query}) group by emoji_sender order by frequency desc;"
message_count_by_day_query = f"select count(*), DATE(date_sent) as date, case cast (strftime('%w', `date_sent`) as integer) " \
                             f"when 0 then 'Sunday' when 1 then 'Monday' when 2 then 'Tuesday' when 3 then 'Wednesday' " \
                             f"when 4 then 'Thursday' when 5 then 'Friday' else 'Saturday' " \
                             f"end as weekday from ({messages_clean_query}) group by weekday ORDER BY CASE weekday WHEN 'Sunday' " \
                             f"THEN 0 WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' " \
                             f"THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 END"
message_count_by_hour_query = f"select count(*), strftime('%H', `date_sent`) as hour from ({messages_clean_query}) group by hour"
top_ten_emojis_query = f"select count(*), emoji from ({reactions_clean_query}) group by emoji order by count(*) desc lIMIT 10"


cursor.execute(total_counts_query)
total_counts = cursor.fetchall()

cursor.execute(reaction_summary_query)
reaction_summary = cursor.fetchall()

cursor.execute(message_count_by_day_query)
message_count_by_day = cursor.fetchall()

cursor.execute(message_count_by_hour_query)
message_count_by_hour = cursor.fetchall()

cursor.execute(top_ten_emojis_query)
top_ten_emojis = cursor.fetchall()


counts_df = pd.DataFrame(total_counts, columns=["Unit", "Total Message Count"])
counts_df_fig = px.bar(counts_df, x="Total Message Count", y="Unit", orientation='h', title="Total Message Counts by Unit")
counts_df_fig.update_layout(yaxis=dict(autorange="reversed"))
reaction_df_freq = pd.DataFrame(reaction_summary, columns=["Unit", "Variety", "Frequency", "Favorite Emoji"])
reaction_df_var = pd.DataFrame(reaction_summary, columns=["Unit", "Variety", "Frequency", "Favorite Emoji"]).sort_values(by="Variety", ascending=False)
reaction_df_fig_freq = px.bar(reaction_df_freq, x="Frequency", y="Unit", orientation='h', title="Number of Total Reactions Used")
reaction_df_fig_freq.update_layout(yaxis=dict(autorange="reversed"))
reaction_df_fig_var = px.bar(reaction_df_var, x="Variety", y="Unit", orientation='h', title="Number of Distinct Reactions Used")
reaction_df_fig_var.update_layout(yaxis=dict(autorange="reversed"))
weekday_df = pd.DataFrame(message_count_by_day, columns=["Total Message Count", "Date", "Day of the Week"])
weekday_message_count = px.bar(weekday_df, x="Day of the Week", y="Total Message Count", title="Message Count by Day of the Week")
hour_df = pd.DataFrame(message_count_by_hour, columns=["Total Message Count", "Hour"])
hour_message_count = px.bar(hour_df, x="Hour", y="Total Message Count", title="Message Count by Hour of the Day")
hour_per_unit_df = pd.DataFrame(columns=["Total Message Count", "Hour", "Unit"])
weekday_per_unit_df = pd.DataFrame(columns=["Total Message Count", "Date", "Day of the Week", "Unit"])
top_emojis_df = pd.DataFrame(top_ten_emojis, columns=["Total Count", "Emoji"])


for u in counts_df.Unit:
    temp_query = f"select count(*), strftime('%H', `date_sent`) as hour from ({messages_clean_query}) where profileFullName = '{u}' group by hour"
    cursor.execute(temp_query)
    temp_df = pd.DataFrame(cursor.fetchall(), columns=["Total Message Count", "Hour"])
    temp_df['Unit'] = u
    hour_per_unit_df = pd.concat([hour_per_unit_df, temp_df])
    temp_query = f"select count(*), DATE(date_sent) as date, case cast (strftime('%w', `date_sent`) as integer) " \
                             f"when 0 then 'Sunday' when 1 then 'Monday' when 2 then 'Tuesday' when 3 then 'Wednesday' " \
                             f"when 4 then 'Thursday' when 5 then 'Friday' else 'Saturday' " \
                             f"end as weekday from ({messages_clean_query}) where profileFullName = '{u}' group by weekday ORDER BY CASE weekday WHEN 'Sunday' " \
                             f"THEN 0 WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' " \
                             f"THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 END"
    cursor.execute(temp_query)
    temp_df = pd.DataFrame(cursor.fetchall(), columns=["Total Message Count", "Date", "Day of the Week"])
    temp_df['Unit'] = u
    weekday_per_unit_df = pd.concat([weekday_per_unit_df, temp_df])

cursor.close()

app.layout = html.Div(
        [html.H1(children='Units Chat Stats', style={'textAlign':'center'}),
         html.H2(children='Totals', style={'textAlign':'center'}),
         dcc.Graph(figure=counts_df_fig, id='total_counts'),
         dcc.Graph(figure=reaction_df_fig_freq, id='reaction_summary_freq'),
         dcc.Graph(figure=reaction_df_fig_var, id='reaction_summary_var'),
         html.Label("Top Ten Emojis Used"),
         dash_table.DataTable(data=top_emojis_df.to_dict('records'), columns=[{"name": i, "id": i} for i in top_emojis_df.columns]),
         dcc.Graph(figure=weekday_message_count, id='weekday_message_count'),
         dcc.Graph(figure=hour_message_count, id='hour_message_count'),
         html.H2(children='By Unit', style={'textAlign':'center'}),
         dcc.Dropdown(counts_df.Unit, 'Chris Moffitt', id='dropdown-selection'),
         dcc.Graph(id='hour_count-graph'),
         dcc.Graph(id='weekday_count-graph'),]
            )


@callback(
    Output('hour_count-graph', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_graph(value):
    figure = px.bar(hour_per_unit_df[hour_per_unit_df.Unit==value], x="Hour", y="Total Message Count",
                  title=f"Total Message Counts Per Hour for {value}")
    return figure

@callback(
    Output('weekday_count-graph', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_graph2(value):
    return px.bar(weekday_per_unit_df[weekday_per_unit_df.Unit==value], x="Day of the Week", y="Total Message Count", title=f"Total Message Counts Per Day of the Week for {value}")



if __name__ == '__main__':
    app.run()
