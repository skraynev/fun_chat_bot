import yaml
import random
from os.path import join
from os import walk
from collections import namedtuple

TASKS_DIR = 'game_tasks'
WAIT_START = 'wait'
IN_PROGRESS = 'in_progress'

Task = namedtuple('Task', ('description', 'time', 'points'))


class EkiGame:

    tasks = {
        1: Task('Поясните слово не используя однокоренные',  60, 1),
        2: Task('Прочтите слово наоборот', 60, 1),
        3: Task('Отправьте смайлики или GIF анимации чтобы объяснить слово', 120, 3),
        4: Task('Вам задают вопросы вы отвечаете только да или нет', 120, 5),
        5: Task('Издавая ТОЛЬКО звуки пояснить слово', 90, 3),
        6: Task('Сочинить стих с рифмой на каждое из слов '
                '(пример: добрый дядя полиглот - утром выпил весь *** (компот))', 120, 4),
        7: Task('Используя только глаголы пояснить слово', 60, 2),
    }

    def __init__(self, players=None):
        self.players = players or {}
        self.players_by_username = {}
        self.iter_player = self.get_players_iterator()
        self.status = WAIT_START
        self.task_types = list(self.tasks)
        self.task_to_words = {task_id: [] for task_id in self.tasks}
        self.load_data_from_files()
        self.stats = {}
        self.context = {
            'task': None,
            'time': None,
            'points': None,
            'player_id': None,
            'player': None,
            'word': None,
            'theme': None,
        }

    def load_data_from_files(self):
        for (path, _, filenames) in walk(TASKS_DIR):
            for file in filenames:
                with open(join(path, file), 'r', encoding="utf8") as fi:
                    data = yaml.safe_load(fi)
                    theme = data.pop('theme')
                    for task_id in data:
                        self.task_to_words[task_id].extend([
                            (theme, word)
                            for word in data[task_id]
                        ])

    def add_player(self, user_id, user_name, first_name):
        if user_id in self.players:
            return '%s уже в игре' % first_name or user_name
        else:
            self.players[user_id] = first_name
            self.players_by_username[user_name] = user_id
            self.stats[user_id] = 0
            return '%s присоединился к игре' % first_name or user_name

    def del_player(self, user_id):
        if user_id in self.players:
            if len(self.players) == 2:
                return 'Невозможно покинуть игру. Достигнуто минимальное количество игроков.'
            elif user_id == self.context['player_id'] and self.status == IN_PROGRESS:
                return 'Невозможно покинуть игру. Текущий игрок должен либо пропустить вопрос, либо ответить.'
            else:
                extra_msg = self.next_turn if user_id == self.context['player_id'] else ''
                del self.stats[user_id]
                return '%s покинул игру\n\n' % self.players.pop(user_id) + extra_msg
        else:
            return 'Указанный пользователь не в игре'

    @property
    def current_turn(self):
        return (
        "*Игрок*: {player}\n"
        "*Задание*: {task}\n"
        "*Время*: {time} секунд\n"
        "*Тема*: {theme}"
        ).format(**self.context)

    def get_task(self):
        if self.status == IN_PROGRESS:
            return 'Невозможно запустить задачу - предыдущий вопрос еще не закончился.', None, None, None
        self.status = IN_PROGRESS
        return None, self.context['player_id'], self.context['word'], self.context['time']

    @property
    def word(self):
        return self.current_word

    @property
    def next_turn(self):
        try:
            task_id = random.choice(self.task_types)
            task = self.tasks[task_id]
            word_pair = random.choice(self.task_to_words[task_id])
            player_id = next(self.iter_player)
            self.context.update({
                'player': self.players[player_id],
                'player_id': player_id,
                'task': task.description,
                'points': task.points,
                'time': task.time,
                'word': word_pair[1],
                'theme': word_pair[0],
            })
            self.task_to_words[task_id].remove(word_pair)
            # NOTE: if task type has not more words in section
            # remove this task_id from task_types
            if not self.task_to_words[task_id]:
                self.task_to_words.pop(task_id, None)
        except Exception as exc:
            return "Sheet happens on next_turn: %s" % str(exc)
        return self.current_turn

    #def get_players_iterator(self):
    #    if not self.players:
    #        yield None
    #    while True:
    #        copy_players = list(self.players)
    #        for player in copy_players:
    #            yield player

    def get_players_iterator(self):
        idx = 0
        while True:
            if not self.players:
                yield None
            players_list = list(self.players)
            if idx > len(players_list):
                idx = 0
            yield players_list[idx]
            idx += 1
            if idx > len(players_list):
                idx = 0

    def add_point(self, player_id, by_username=False):
        if by_username:
            player_id = self.players_by_username.get(player_id)
        if player_id in self.players:
            self.stats[player_id] += 1 if by_username else self.context['points']
            return self.stats[player_id]
        else:
            return False

    def remove_point(self, player_id, by_username=False):
        if by_username:
            player_id = self.players_by_username.get(player_id)
        if player_id in self.players:
            if self.stats[player_id] > 0:
                self.stats[player_id] -= 1
                return self.stats[player_id]
            else:
                return 'Невозможно сделать количество очков меньше 0'
        else:
            return False

    @property
    def show_top(self):
        top_msg = ''
        for user_id, username in self.players.items():
            top_msg += '\n%s  ----  %d' % (username, self.stats[user_id])
        return 'Рейтинг:%s' % top_msg

    def cancel_question(self):
        if self.status == WAIT_START:
            return False, 'Нет активного вопроса, который можно пропустить.'
        self.status = WAIT_START
        return True, 'Вопрос пропущен!'

    def question_is_answered(self):
        if self.status == WAIT_START:
            return 'Нет активного вопроса, который можно засчитать отгаданным.'
        self.status = WAIT_START
        self.add_point(self.context['player_id'])
        return 'Вопрос отгадан!'

    @staticmethod
    def parse_players_telebot(data):
        players = data.text.split(' ')
        return players

    def do_random_sheet(self):
        if random.random() < 0.0000001:
            if random.choice([True, False]):
                self.add_point(self.context['player_id'])
                return 'Поздравляем! Вам улабнулась удача и выполучили свое очко'
            else:
                self.remove_point(self.context['player_id'])
                return 'Сожалеем! Вы утратили свое очко'
        return ''
