#include <stdio.h>
#include <math.h>
#include <String.h>

int i=0;

struct OSS{
	char* OS;
	int i;
};

struct NSS{
	float* NS;
	int i;
};

int PRT(char op){
	switch(op){
		case '=':return 0;break;
		case '+':return 1;break;
		case '-':return 1;break;
		case '*':return 2;break;
		case '/':return 2;break;
		case '^':return 3;break;
		default :printf("ERROR_PRT\n");return -1;
	}
}

int NS_PUSH(float* NS,int vct_NS,float push){
	if(vct_NS<19){
		NS[vct_NS+1]=push;
		vct_NS++;
		return vct_NS;
	}
	else{
		printf("ERROR_NS_PUSH\n");
		return -1;
	}
}

int NS_POP(float* NS,int vct_NS){
	if(vct_NS>=-1){
		NS[vct_NS]=0;
		vct_NS--;
		return vct_NS;
	}
	else{
		printf("ERROR_NS_POP\n");
		return -1;
	}
}

int OS_PUSH(char* OS,int vct_OS,char push){
	if(vct_OS<19){
		OS[vct_OS+1]=push;
		vct_OS++;
		return vct_OS;
	}
	else{
		printf("ERROR_OS_PUSH\n");
		return -1;
	}
}

int OS_POP(char* OS,int vct_OS){
	if(vct_OS>0){
		OS[vct_OS]=0;
		vct_OS--;
		return vct_OS;
	}
	else{
		printf("ERROR_OS_POP\n");
		return -1;
	}
}

float Compute(float y,float x,char op){
	switch(op){
		case '+':return (y+x);break;
		case '-':return (y-x);break;
		case '*':return (y*x);break;
		case '/':if(x==0) return 404;else return (y/x);break;
		case '^':return (pow(y,x));break;
		default :printf("ERROR_Compute\n");return -1;
	}
}

int main(){
	float x,y,r;
	int l;
	char op,anything[100];
	float NS[20]={0};
	char OS[20]={0};
	struct OSS OS1;
	struct NSS NS1;
	OS1.OS=OS;
	NS1.NS=NS;
	OS1.i=-1;
	NS1.i=-1;
	OS1.i=OS_PUSH(OS,-1,'=');
	printf("请输入表达式：");
	gets(anything);
	l=strlen(anything);
	for(i=0;i<l;i++){
		if(anything[i]=='='||anything[i]=='+'||anything[i]=='-'||anything[i]=='*'||anything[i]=='/'||anything[i]=='^'){
			if(PRT(anything[i])>PRT(OS[OS1.i])){
				OS1.i=OS_PUSH(OS,OS1.i,anything[i]);
				continue;
			}
			else if(anything[i]=='='&&OS[OS1.i]=='='){
				r=NS[NS1.i];
				NS1.i=NS_POP(NS,NS1.i);
			}
			else if(PRT(anything[i])<=PRT(OS[OS1.i])){
				x=NS[NS1.i];
				NS1.i=(NS_POP(NS,NS1.i));
				y=NS[NS1.i];
				NS1.i=(NS_POP(NS,NS1.i));
				op=OS[OS1.i];
				OS1.i=(OS_POP(OS,OS1.i));
				r=Compute(y,x,op);
				NS1.i=(NS_PUSH(NS,NS1.i,r));
				i--;
				continue;
			}
		}
		else{
			NS1.i=(NS_PUSH(NS,NS1.i,((float)anything[i]-48.0)));
			continue;
		}
	}
	printf("%f",r);
	return 0;
}