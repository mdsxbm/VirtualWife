from .competition_record_service import *
from .competition_service import *
from .riddle_service import *
from .leaderboard_service import *
from blivedm.core.chat_priority_queue_management import *
import logging

'''后续看要不要放到缓存'''

# 当前谜题下标
current_riddle_index = 0
# 当前谜题答案
current_riddle_answer = ''
# 当前谜题类型
current_riddle_type = ''
# 当前谜题描述
current_riddle_description = ''
# 当前比赛ID
current_competition_id = None
# 当前比赛轮次
current_competition_turn = 1;

'''开始你画我猜游戏'''
def start_competition():

    global current_competition_id
    global current_competition_turn

    # 1.创建比赛
    competition_dto = CompetitionDTO(name='test',turn=0)
    db_competition = CompetitionHandle.create(competition_dto)
    logging.info('[BIZ] db_competition:'+json.dumps(db_competition))
    current_competition_id = db_competition["id"]
    current_competition_turn = 1

    # content =  f'开始新一轮你画我猜游戏了，嘻嘻~，小伙伴们你们准备好了吗？'
    # message_body = {
    #     "type":"game",
    #     "content": content,
    #     "cmd" : ''
    # }
    # put_chat_message(MessagePriority.GAME_MESSAGE,message_body)
    logging.info('[BIZ]开始新一轮的你画我猜游戏')

    # 2.开始下一个答题
    next_riddle()

'''提交谜题答案'''
def commit_riddle_answer(user_name:str,riddle_answer:str):

    global current_competition_id
    global current_riddle_answer
    global current_competition_turn

    if current_competition_id is None:
        return
    
    ## 格式化一下答案，去除#
    riddle_answer = riddle_answer.lstrip('#')
    
    # 1.查询当前比赛实体
    competition =  CompetitionQuery.get(current_competition_id)
    
    # 2.查询用户当前比赛记录，如果没有比赛记录，初始化比赛记录
    competition_record = CompetitionRecordQuery.getByCompetitionIdAndParticipantName(competition_id=current_competition_id,participant_name=user_name)
    if competition_record is None:
        competition_record_dto = CompetitionRecordDTO(competition_id=current_competition_id,participant_name=user_name,score=0)
        competition_record = CompetitionRecordHandle.create(competition_record_dto)
        logging.info(f'[BIZ]{user_name}第一次答题，初始化比赛记录')

    # 3.判断当前用户输入的谜题答案是否正确
    riddle_match = riddle_answer == current_riddle_answer;
    logging.info(f'[BIZ]{user_name}回答问题，riddle_answer：{riddle_answer} current_riddle_answer:{current_riddle_answer}')
    if(riddle_match):
        # 4.如果正确，比赛分数+1，保存到数据库，发送消息给前端刷新
        score = competition_record.score + 1
        competition_record_dto = CompetitionRecordDTO(id=competition_record.id,competition_id=competition_record.competition_id,participant_name=competition_record.participant_name,score=score)
        CompetitionRecordHandle.update(competition_record_dto)

        # 5.回答错误，发送消息
        cmd_str = f'{user_name}在你画我猜游戏中回答正确，请祝福一下他'
        content = f'{user_name}回答正确'
        message_body = {
            "type":"system",
            "content":content,
            'cmd': cmd_str
        }
        put_chat_message(MessagePriority.GAME_ERPLY_MESSAGE,message_body)

        # 6.继续下一轮游戏
        next_riddle()

    else:
        # 5.回答错误，发送消息
        cmd_str = f'{user_name}在你画我猜游戏中回答错误，请鼓励一下他'
        content = f'{user_name}回答错误'
        message_body = {
            "type":"system",
            "content": content,
            'cmd': cmd_str
        }
        put_chat_message(MessagePriority.GAME_ERPLY_MESSAGE,message_body)
   
    # 6.判断当前轮次，如果等于5，结束比赛
    logging.info(f'当前游戏轮次：{current_competition_turn}')
    if(current_competition_turn > 5):
        end_comptition()
    else:
        competition = CompetitionDTO(id=current_competition_id,turn=current_competition_turn)
        CompetitionHandle.update(competition)

def end_comptition():

    if current_competition_id is None:
        return
    
    # 1.查询当前比赛实体
    competition =  CompetitionQuery.get(current_competition_id)

    # 2.查询当前比赛记录，获取分数最高者
    competition_record = CompetitionRecordQuery.getMaxScoreCompetitionRecord(competition_id=current_competition_id)
    participant_name = competition_record.participant_name

    # 3.设置当前比赛的胜利者
    CompetitionDTO(id=current_competition_id,victor_name=participant_name,end_date=timezone.now())

    # TODO 4.更新排行榜

    # 5.发送比赛结束消息
    cmd_str = f'{participant_name}获得你画我猜游戏胜利'
    content = f'本轮你画我猜游戏结束，恭喜{participant_name}是本轮比赛的获胜者，开始下一轮比赛'
    message_body = {
        "type":"system",
        "content": content,
        'cmd': cmd_str
    }
    put_chat_message(MessagePriority.GAME_ERPLY_MESSAGE,message_body)

    # 6.开始下一轮比赛
    start_competition()

def next_riddle():

    global current_riddle_index
    global current_riddle_answer
    global current_riddle_type
    global current_riddle_description
    global current_competition_turn
    
    # 1. 通过当前下标获取谜题
    riddle = getRandomRiddle();
    current_riddle_answer = riddle.riddle_answer
    current_riddle_type = riddle.riddle_type
    current_riddle_description = riddle.riddle_description

    # 2. 发送消息给前端渲染新的谜题
    cmd_str =  {"imageId":riddle.riddle_image_id}
    message_body = {
        "type":"game",
        'cmd': cmd_str
    }
    put_chat_message(MessagePriority.GAME_MESSAGE,message_body)

    # 3. 比赛轮次+1、谜题下标+1
    current_riddle_index = current_riddle_index + 1
    current_competition_turn = current_competition_turn + 1

'''随机获取谜题'''
def getRandomRiddle():
    global current_riddle_index
    riddles =  RiddleQuery.all()
    riddle = riddles[current_riddle_index]
    return riddle