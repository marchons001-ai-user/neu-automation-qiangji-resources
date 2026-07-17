#include <bits/stdc++.h>
#include <windows.h>
using namespace std;

int s1=1,s2=0,i=0,j=0;
int a[16]={0};
int b[16]={0};
int c[16]={0};

int P(int s){
	s--;
	return s;
}

int V(int s){
	s++;
	return s;
}

//生成随机数
int get_random(){
	static default_random_engine e(time(0));
	static uniform_int_distribution<unsigned> u(0,9);
	return u(e);
}

void productor(){
	//生产物品
	b[0]=2;
	b[1]=0;
	b[2]=2;
	b[3]=3;
	b[4]=5;
	b[5]=7;
	b[6]=3;
	b[7]=1;
	for(int m=8;m<16;m++){
		b[m]=get_random();
	}
	if(s1>=1){
		s1=P(s1);
		//清除原本占用并把物品放入缓存区
		SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE),13);
		for(int m=0;m<16;m++){
			a[m]=b[m];
		}
	}
	s2=V(s2);
	i++;
	cout<<"					生产者任务<"<<i<<">已完成。"<<endl;
}

void consumer(){
	if(s2>=1){
		s2=P(s2);
		//取出物品
		for(int m=0;m<16;m++){
			c[m]=a[m];
		}
	}
		s1=V(s1);
		j++;
		//消费物品
		SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE),11);
		for(int m=0;m<16;m++){
			cout<<c[m];
		}
		cout<<"_anonymous";
		cout<<"	        消费者任务<"<<j<<">已完成!"<<endl;
}

int main(){
	for(int k=0;k<5;k++){
		productor();
		consumer();
		cout<<endl;
	}
	return 0;
}
