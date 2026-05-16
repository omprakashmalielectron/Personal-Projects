import json
from typing import List
class intern:
    def __init__(self,name: str="",role: str="",daily_hours: int=0, daily_tasks: str=""):
        self.name=name.strip().title()
        self.role=role.strip().title()
        try:
            daily_hours=int(daily_hours)
            if 0<daily_hours<24:
                self.daily_hours=int(daily_hours)
            else:
                raise ValueError("Hours entered is not in valid range")
        except ValueError:
            raise ValueError("Hours entered must be Integer")
        self.daily_tasks=daily_tasks.strip()
        self.days=0
        self.logged_hours:List[int]=[]
        self.logged_tasks:List[str]=[]
    @staticmethod
    def get_info():
        name=input("Enter intern name: ")
        role=input("Enter inter role: ")
        daily_hours=input("Enter intern hrs: ")
        daily_task=input("Enter intern daily_task: ")
        i=intern(name,role,daily_hours,daily_task)
        return i
    ### taking record of interns daily activity
    def get_record(self):
        try:
            self.days=int(input("Enter number of days to record: "))
            if self.days<=0:
                raise ValueError("Number of days must be strictly positive")
        except:
            raise ValueError("Number of days must be positive")
            return
            
        # getting info for inters daily activity
        for i in range(self.days):
            try:
                hrs=int(input(f"Enter number of hrs worked on day {i}: "))
                if 0<hrs<24:
                    self.logged_hours.append(hrs)
                else:
                    raise ValueError("Hours entered is not in valid range")
            except ValueError:
                raise ValueError("Hours entered must be Integer")
                return
            self.logged_tasks.append(input(f"Enter task worked on day {i}:"))
    # saving and loading intern data in .json format
    def to_dict(self):
        return {
            "name": self.name,
            "role": self.role,
            "daily_hours": self.daily_hours,
            "daily_tasks": self.daily_tasks,
            "days": self.days,
            "logged_hours": self.logged_hours,
            "logged_tasks": self.logged_tasks,
        }    
    def to_json(self,filename="intern.json"):
        with open(filename,"w") as f:
            json.dump(self.to_dict(),f,indent=4)
    def from_json(filename="intern.json"):
        with open(filename,"r") as f:
            x=json.load(f)
        i1=intern(x["name"],x["role"],x["daily_hours"],x["daily_tasks"])
        i1.days=x["days"]
        i1.logged_hours=x["logged_hours"]
        i1.logged_tasks=x["logged_tasks"]
        return i1
    # now comes intern evaluation part with buisness perspective
    def total_working_hrs(self):
        print(f"Total working hours(aggregated over all days): {sum(self.logged_hours)}")
    def average_working_hrs(self):
        print(f"Average working hours of intern: {sum(self.logged_hours)/self.days}")
    def get_summary(self):
        print(f"INTERN SUMMARY\n"f"Intern name: {self.name}\n" f"Intern role {self.role} \n" 
              f"Intern hrs {self.daily_hours} \n" f"Inter daily task {self.daily_tasks}")
    def get_activity_summary(self):
        self.get_summary()
        print(f"Working hrs detail: \n") 
        self.total_working_hrs()
        self.average_working_hrs()
        print(f"DAILY TASK DETAILS: \n")
        for i in range(self.days):
            print(f"Activity on day {i}: " f"Worked for {self.logged_hours[i]} hrs." f"Worked on task {self.logged_tasks[i]}")



if __name__ == "__main__":
    intern1 = intern.get_info()
    intern1.get_record()

    intern1.to_json()

    loaded = intern.from_json()
    loaded.get_activity_summary()