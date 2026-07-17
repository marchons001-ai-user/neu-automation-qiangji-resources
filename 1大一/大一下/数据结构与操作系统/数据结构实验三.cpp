#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define length 400
int disk[length],diskl=length;//默认磁盘空闲块大小400
int MFD_n=10,UFD_n=9,PerUOF_n=6,ofP/*UOF循环下标*/=0;
typedef struct MFD
{
    char name[20];
    int content_Location;
} MFD;
typedef struct UFD //uf
{
    char username[10];
    char fname[20];
    char fattr[10];//文件属性
    int recordl;
    int addrf;
} UFD;
typedef struct UOF //of
{
    char file_Name[20];
    char fattr[12];
    int recordl;
    int status;
    int read;
    int write;
} UOF;
typedef struct users
{
    char    name[9];
    char    pwd[9];
} users;
users usrarray[10] = /*用户账号密码数据库*/
{
    "user001","user001",
    "user002","user002",
    "user003","user003",
    "user004","user004",
    "user005","user005",
    "user006","user006",
    "user007","user007",
    "user008","user008",
    "user009","user009",
    "user010","user010",
};

int menu();//操作菜单函数
void InitMFD(MFD* mf[],int n);//初始化一级目录
void InitUFD(UFD* uf[],int n);//初始化二级目录
void InitUOF(UOF* of[]);//初始化已打开的文件目录
int LogIn(char USERname[],char USERpsd[],MFD* mf[],int n);//用户登录
void showlist(char user[],UFD* uf[]);//列出文件列表
int CreateFile(UOF* of[],UFD* uf[],char user[]);//创建新文件
int Delete(UOF* of[],UFD* uf[],char user[]);//删除文件
int Open(UOF* of[],UFD* uf[],char user[]);//打开文件
int Close(UOF* of[],char user[]);//关闭文件
int Read(UOF* of[],char user[]);//读文件
int Write(UOF* of[],UFD* uf[],char user[]);//写文件

int main()
{
    MFD* mf[MFD_n];//一级目录表
    UFD* uf[MFD_n*10];//二级目录表
    UOF* of[PerUOF_n];//已打开的文件表
    InitMFD(mf,MFD_n);//初始化原始数据
    InitUFD(uf,UFD_n);
    InitUOF(of);
    char USERname[9],USERpsd[9];//待登录的用户名与登录密码
    if(LogIn(USERname,USERpsd,mf,MFD_n))//登录成功时,LogIn()返回1
    {
        while(1)
        {
            switch(menu())
            {
            case -1: // end 命令
                printf("结束程序！");
                return 0;
            case 1: // list 命令
                showlist(USERname,uf);
                break;
            case 2: // create 命令
                CreateFile(of,uf,USERname);
                break;
            case 3: // delete 命令
                Delete(of,uf,USERname);
                break;
            case 4: // open 命令
                Open(of,uf,USERname);
                break;
            case 5: // close 命令
                Close(of,USERname);
                break;
            case 6: // read 命令
                Read(of,USERname);
                break;
            case 7: // write 命令
                Write(of,uf,USERname);
                break;
            case 0: // change 命令：切换用户
                LogIn(USERname,USERpsd,mf,MFD_n);
                break;
            }
        }
    }
    return 0;
}
int menu()
{
    char dos[20];
    printf("\n* * * * * * * * * * * * * * * * * * * * * * * * * * *\n");
    printf("* change:切换用户                                   *\n");
    printf("* list:  查看你的文件列表   create:调用建立文件程序 *\n");
    printf("* delete:调用删除文件程序   open:  调用打开文件程序 *\n");
    printf("* close: 调用关闭文件程序   read:  调用读文件程序   *\n");
    printf("* write: 调用写文件程序     end:   退出程序         *\n");
    printf("* * * * * * * * * * * * * * * * * * * * * * * * * * *\n");
    printf("请输入相应命令：");
    while(1)
    {
        scanf("%s",&dos);
        if((strcmp(dos,"change")==0)||(strcmp(dos,"list")==0)||(strcmp(dos,"create")==0)||(strcmp(dos,"delete")==0)||(strcmp(dos,"open")==0)||(strcmp(dos,"close")==0)||(strcmp(dos,"read")==0)||(strcmp(dos,"write")==0)||(strcmp(dos,"end")==0))
            break;
        else
            printf("输入的命令错误，请重新输入：");
    }
    int no;
    if(strcmp(dos,"change")==0)
        no=0;
    if(strcmp(dos,"list")==0)
        no=1;
    if(strcmp(dos,"create")==0)
        no=2;
    if(strcmp(dos,"delete")==0)
        no=3;
    if(strcmp(dos,"open")==0)
        no=4;
    if(strcmp(dos,"close")==0)
        no=5;
    if(strcmp(dos,"read")==0)
        no=6;
    if(strcmp(dos,"write")==0)
        no=7;
    if(strcmp(dos,"end")==0)
        no=-1;
    return no;
}
void InitMFD(MFD* mf[],int n)
{
    int i,j;
    for(i=0; i<n; i++)
        mf[i] = (MFD*)malloc(sizeof(MFD));
    strcpy(mf[0]->name,"user001");
    mf[0]->content_Location=20;
    strcpy(mf[1]->name,"user002");
    mf[1]->content_Location=60;
    strcpy(mf[2]->name,"user003");
    mf[2]->content_Location=100;
    strcpy(mf[3]->name,"user004");
    mf[3]->content_Location=140;
    strcpy(mf[4]->name,"user005");
    mf[4]->content_Location=180;
    strcpy(mf[5]->name,"user006");
    mf[5]->content_Location=220;
    strcpy(mf[6]->name,"user007");
    mf[6]->content_Location=260;
    strcpy(mf[7]->name,"user008");
    mf[7]->content_Location=300;
    strcpy(mf[8]->name,"user009");
    mf[8]->content_Location=340;
    strcpy(mf[9]->name,"user010");
    mf[9]->content_Location=380;
    for(j=0; j<length; j++)
        disk[j] = 1;
}
void InitUFD(UFD* uf[],int n)
{
    int i;
    for(i=0; i<n; i++)
        uf[i] = (UFD*)malloc(sizeof(UFD));
    strcpy(uf[0]->username,"user001");
    strcpy(uf[0]->fname,"u1f1");
    strcpy(uf[0]->fattr,"r");
    uf[0]->recordl=10;
    strcpy(uf[1]->username,"user001");
    strcpy(uf[1]->fname,"u1f2");
    strcpy(uf[1]->fattr,"r");
    uf[1]->recordl=20;
    strcpy(uf[2]->username,"user001");
    strcpy(uf[2]->fname,"u1f3");
    strcpy(uf[2]->fattr,"r");
    uf[2]->recordl=30;
    strcpy(uf[3]->username,"user002");
    strcpy(uf[3]->fname,"u2f1");
    strcpy(uf[3]->fattr,"r");
    uf[3]->recordl=25;
    strcpy(uf[4]->username,"user002");
    strcpy(uf[4]->fname,"u2f2");
    strcpy(uf[4]->fattr,"r");
    uf[4]->recordl=35;
    strcpy(uf[5]->username,"user002");
    strcpy(uf[5]->fname,"u2f3");
    strcpy(uf[5]->fattr,"r");
    uf[5]->recordl=15;
    strcpy(uf[6]->username,"user002");
    strcpy(uf[6]->fname,"u2f4");
    strcpy(uf[6]->fattr,"w");
    uf[6]->recordl=5;
    strcpy(uf[7]->username,"user005");
    strcpy(uf[7]->fname,"u5f1");
    strcpy(uf[7]->fattr,"w");
    uf[7]->recordl=40;
    strcpy(uf[8]->username,"user005");
    strcpy(uf[8]->fname,"u5f2");
    strcpy(uf[8]->fattr,"w");
    uf[8]->recordl=45;
    for(i=0; i<n; i++)
    {
        uf[i]->addrf=length-diskl;
        diskl = diskl - uf[i]->recordl;
    }
    for(i=0; i<(length - diskl); i++)
        disk[i]=0;
}
void InitUOF(UOF* of[])
{
    int i;
    for(i=0; i<6; i++)
    {
        of[i] = (UOF*)malloc(sizeof(UOF));
        strcpy(of[i] -> file_Name,"null");
    }
}
int LogIn(char USERname[],char USERpsd[],MFD* mf[],int n)
{
    int i,j,k=-1/*k为查询标志符*/;
    printf("当前文件系统一级目录下的所有用户:");
    for(i=0; i<n; i++)
        printf("%s ",mf[i]->name);
    printf("\n\n请输入你的用户名：");
    scanf("%s",USERname);
    for(i=0; i<n; i++)
    {
        if(strcmp(USERname,mf[i]->name)==0)
        {
            k=i;
            break;
        }
    }
    if(k!=-1)
    {
        printf("请输入登录密码：  ");
        scanf("%s",USERpsd);
        for(j=0; j<10; j++)
        {
            if(strcmp(USERname,usrarray[j].name)==0)
            {
                if(strcmp(USERpsd,usrarray[j].pwd)==0)
                {
                    printf("用户%s已成功登录！\n",USERname);
                    return 1;
                }
                else
                {
                    printf("密码输入错误,请重新登录！\n");
                    LogIn(USERname,USERpsd,mf,n);
                }
            }
        }
    }
    else
    {
        printf("用户%s是非法用户，请重新输入合法用户名！\n",USERname);
        LogIn(USERname,USERpsd,mf,n);
    }
    return 0;
}
void showlist(char user[],UFD* uf[])
{
    int i,k=-1,n=UFD_n;
    for(i=0; i<n; i++)
        if(strcmp(user,uf[i]->username)==0)
            k++;
    if(k!=-1)
    {
        printf("\n当前用户%s拥有%d个文件：\n",user,k+1);
        printf("  文件名   属性   记录长度   文件地址\n");
        for(i=0; i<n; i++)
            if(strcmp(user,uf[i]->username)==0)
                printf("   %s    %s      %d        %d\n",uf[i]->fname,uf[i]->fattr,uf[i]->recordl,uf[i]->addrf);
    }
    else
        printf("当前用户下没有任何文件！\n");

/*
    printf("UFD:n=%d\n",n);
    for(i=0; i<n; i++)
            printf("   %s    %s      %d        %d\n",uf[i]->fname,uf[i]->fattr,uf[i]->recordl,uf[i]->addrf);
*/
}
int Read(UOF* of[],char user[])
{
    int i;
    char newfile[15];
    printf("请输入要读的文件名：");
    scanf("%s",&newfile);
    for(i=0; i<6; i++)
        if(strcmp(of[i]->file_Name,newfile)==0)
        {
            printf("该文件的读指针：%d,读内容的地址从%d到%d\n",of[i]->read,of[i]->read,of[i]->read+of[i]->recordl);
            printf("修改‘读指针’，查看对应地址的记录内容……\n");
            printf("%s文件读成功！\n",newfile);
            return 0;
        }
    printf("文件不存在，不能读！\n");
    return 0;
}
int Close(UOF* of[],char user[])
{
    int i;
    char newfile[15];
    printf("请输入要关闭的文件名：");
    scanf("%s",&newfile);
    for(i=0; i<6; i++)
    {
        if((strcmp(of[i]->file_Name,newfile)==0)&&((of[i]->status==1)||(of[i]->status==0)))
        {
            strcpy(of[i]->file_Name,"null");
            strcpy(of[i]->fattr,"null");
            of[i]->recordl=0;
            of[i]->write=0;
            ofP=(ofP-1)%6;//循环修改UOF开文件指针；
            printf("%s文件关闭成功！\n",newfile);
            return 0;
        }
    }
    printf("%s文件为关闭状态！\n",newfile);
    return 0;
}
int Write(UOF* of[],UFD* uf[],char user[])
{
    int i, k=-1;
    char newfile[15];
    printf("请输入要写的文件名：");
    scanf("%s",&newfile);
    for(i=0; i<6; i++)
        if(strcmp(of[i]->file_Name,newfile)==0)
        {
            if(of[i]->status==1)
            {
                printf("模拟将记录信息写到‘写指针’指出的磁盘块中……\n");
                of[i]->write=length - diskl;
                disk[length - diskl]=0;
                diskl-=1;
                printf("%s写文件成功！\n",newfile);
            }
            else
            {
                if(strcmp(of[i]->fattr,"r")==0)
                    printf("操作不合法，不能写！\n");
                else
                {
                    printf("是否顺序修改？'y'或'n'|请输入：");
                    int order;
                    scanf("%d",&order);
                    if(order==1)
                    {
                        printf("已取出该文件写指针地址：%d\n","请输入新的写指针：",of[i]->write);
                        scanf("%d",of[i]->write);
                    }
                    else
                        printf("已取出该文件指定记录的块号：%d\n",uf[k]->addrf);
                    printf("模拟把记录信息写入到磁盘中……");
                    printf("%s文件写成功！\n",newfile);
                }
            }
            return 0;
        }
    printf("文件不存在，不能写！\n");
    return 0;
}
int Open(UOF* of[],UFD* uf[],char user[])
{
    int i,counter,j=-1,k=-1;
    char newfile[15],opType[4];
    printf("UFD_n:%d,请输入要打开的文件名和操作类型：",UFD_n);
    scanf("%s%s",&newfile,&opType);
    for(i=0; i<UFD_n; i++)
        if((strcmp(uf[i]->username,user)==0)&&(strcmp(uf[i]->fname,newfile)==0))
        {
            k=i;
            break;
        }
    if(k == -1)
    {
        printf("文件不存在，不能打开！\n");
        return 0;
    }
    else
    {
        if(ofP<6)
        {
            for(i=0; i<6; i++)
                if(strcmp(of[i]->file_Name,newfile)==0)
                {
                    j=i;
                    if(of[i]->status==1)
                        printf("正在建立，不能打开！\n");
                    else
                        printf("文件已打开！\n");
                    return 0;
                }
            if(j==-1)
            {
                if(strcmp(uf[k]->fattr,opType)==0)
                {
                    strcpy(of[ofP]->file_Name,newfile);
                    strcpy(of[ofP]->fattr,opType);
                    of[ofP]->recordl=uf[k]->recordl;
                    of[ofP]->write = uf[k]->addrf;
                    of[ofP]->read = uf[k]->addrf;
                    of[ofP]->status = 0;
                    ofP=(ofP+1)%6;//循环修改UOF开文件指针；
                    printf("%s 文件打开成功！\n",newfile);
                }
                else
                    printf("操作不合法，不能打开文件！\n");
            }
        }
        else
        {
            printf("最多只可打开6个文件，请关闭其他文件！");
            return 0;
        }
    }
    return 0;
}
int Delete(UOF* of[],UFD* uf[],char user[])
{
    int i,j=-1,k=-1;
    char newfile[15];
    printf("请输入要删除的文件名：");
    scanf("%s",&newfile);
    for(i=0; i<UFD_n; i++)
        if((strcmp(uf[i]->username,user)==0)&&(strcmp(uf[i]->fname,newfile)==0))
        {
            k=i;
            break;
        }
    if(k == -1)
    {
        printf("请按要求输入正确命令！\n");
    }
    else
    {
        for(i=0; i<6; i++)
            if(strcmp(of[i]->file_Name,newfile)==0)
            {
                j=i;
                strcpy(of[i]->file_Name,"null");
                strcpy(of[i]->fattr,"null");
                of[i]->recordl=-1;
                of[i]->write = -1;
                of[i]->read = -1;
                ofP=(ofP-1)%6;//循环修改UOF开文件指针；
            }
    }
    diskl = diskl + uf[k]->recordl;
    for(i=length-diskl; i<length; i++)
        disk[i] = 1;
    strcpy(uf[k]->username,"null");
    strcpy(uf[k]->fname,"null");
    strcpy(uf[k]->fattr,"null");
    uf[k]->recordl=-1;
    uf[k]->addrf=-1;
    free(uf[k]);
    printf("%s文件删除成功！\n",newfile);
    return 0;
}
int CreateFile(UOF* of[],UFD* uf[],char user[])
{
    int newrecordl,i,k=-1,n=UFD_n;
    char newfile[15],newfattr[4];
    printf("请输入要创建的文件名,文件长度及属性：");
    scanf("%s%d%s",&newfile,&newrecordl,&newfattr);
    for(i=0; i<n; i++)
        if(strcmp(newfile,uf[i]->fname)==0)
        {
            printf("有同名文件，不能创建！\n");
            return 0;
        }
    for(i=0; i<n; i++)
        if(strcmp(user,uf[i]->username)==0)
            k++;
    if(k>=10)
    {
        printf("在UFD中无空登记栏，不能创建！\n");
        return 0;
    }
    else
    {
        if((diskl - newrecordl)<0)
        {
            printf("磁盘中无空闲块，不能创建！\n");
            return 0;
        }
        else
        {
            diskl = diskl - newrecordl;
            for(i=0; i<length-diskl; i++)
                disk[i] = 0;
            uf[n] = (UFD*)malloc(sizeof(UFD));
            strcpy(uf[n]->username,user);
            strcpy(uf[n]->fname,newfile);
            strcpy(uf[n]->fattr,newfattr);
            uf[n]->recordl=newrecordl;
            uf[n]->addrf=length-diskl;
            strcpy(of[ofP]->file_Name,newfile);
            strcpy(of[ofP]->fattr,newfattr);
            of[ofP]->recordl=newrecordl;
            of[ofP]->status=1;
            of[ofP]->write=newrecordl;
            UFD_n++;
            ofP=(ofP+1)%6;
            printf("%s 文件创建成功！\n",newfile);
        }
    }
    return 0;
}
