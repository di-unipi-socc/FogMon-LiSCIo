#ifndef UICONNECTION_HPP_
#define UICONNECTION_HPP_

#include <string>
#include <vector>
#include "message.hpp"
#include "report.hpp"

class UIConnection {

public:
    UIConnection(std::string ip = "");
    ~UIConnection();

    bool sendTopology(std::vector<Report::report_result> report);
    bool sendChangeRole(Message::leader_update update);
private:
    std::string ip;
};

#endif